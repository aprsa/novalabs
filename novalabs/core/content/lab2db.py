"""
Load lab content from TOML/MD files into the database.

This module reads the content files and populates the database tables.
"""

import logging
from pathlib import Path
from typing import Optional
import toml

from ..models import Lab, Question, Exercise, ExerciseTask
from .schemas import QuizConfig, ExerciseConfig
from .discovery import LabInfo, validate_lab_structure, compute_content_hash

logger = logging.getLogger(__name__)


def load_markdown_file(path: Path) -> str:
    """Load content from a markdown file."""
    if path.exists():
        return path.read_text(encoding='utf-8')
    return ""


async def load_lab_content(info: LabInfo, force: bool = False) -> Optional[Lab]:
    """
    Load a prevalidated lab into the database (no re-validation).

    Args:
        info: LabInfo returned by discovery/validation
        force: If True, reload even if content hash matches

    Returns:
        The Lab model instance, or None if invalid
    """

    if not info.is_valid or info.config is None:
        logger.error(f"Lab validation failed for {info.path}")
        for err in info.errors:
            logger.error(f"  {err.message}")
        return None

    config = info.config
    lab_path = info.path
    content_dir = lab_path / 'content'

    # Check if already loaded with same hash
    existing = await Lab.get_or_none(slug=config.lab.slug)
    content_hash = info.content_hash or compute_content_hash(lab_path)

    if existing and not force:
        if existing.content_hash == content_hash:
            logger.info(f"Lab {config.lab.slug} unchanged, skipping")
            return existing

    logger.info(f"Loading lab: {config.lab.slug}")

    # Create or update lab
    if existing:
        lab = existing
        # Clear existing questions and exercises
        await _clear_lab_content(lab)
    else:
        lab = Lab(slug=config.lab.slug)

    # Update lab fields
    lab.title = config.lab.title
    lab.description = config.lab.description or ""
    lab.version = config.lab.version
    lab.passing_score = config.lab.passing_score
    lab.content_hash = content_hash
    lab.content_path = str(lab_path)

    # Load briefing content
    briefing_path = content_dir / config.briefing.file
    lab.briefing_content = load_markdown_file(briefing_path)

    # Set max points
    lab.pre_quiz_max_points = 10.0
    lab.post_quiz_max_points = 10.0

    await lab.save()

    # Load pre-quiz questions
    pre_quiz_path = content_dir / config.pre_quiz.file
    await _load_quiz(lab, pre_quiz_path, 'pre')

    # Load post-quiz questions
    post_quiz_path = content_dir / config.post_quiz.file
    await _load_quiz(lab, post_quiz_path, 'post')

    # Load exercises
    exercises_dir = content_dir / 'exercises'
    for i, ex_ref in enumerate(config.exercises):
        ex_dir = exercises_dir / ex_ref.dir
        await _load_exercise(lab, ex_dir, ex_ref.max_points, i + 1)

    logger.info(f"Loaded lab {config.lab.slug}: "
                f"{len(config.exercises)} exercises, "
                f"pre-quiz + post-quiz")

    return lab


async def _clear_lab_content(lab: Lab) -> None:
    """Remove all questions and exercises for a lab (for reloading)."""
    # Delete questions
    await Question.filter(lab_id=lab.id).delete()

    # Delete exercise tasks first, then exercises
    exercises = await Exercise.filter(lab_id=lab.id)
    for ex in exercises:
        await ExerciseTask.filter(exercise_id=ex.id).delete()
    await Exercise.filter(lab_id=lab.id).delete()


async def _load_quiz(lab: Lab, quiz_path: Path, phase: str) -> None:
    """Load quiz questions from a TOML file."""
    if not quiz_path.exists():
        logger.warning(f"Quiz file not found: {quiz_path}")
        return

    try:
        raw = toml.load(quiz_path)
        config = QuizConfig(**raw)
    except Exception as e:
        logger.error(f"Failed to load quiz {quiz_path}: {e}")
        return

    for i, q in enumerate(config.questions):
        await Question.create(
            lab_id=lab.id,
            phase=phase,
            question_text=q.text,
            options=q.options,
            correct_index=q.correct,
            sort_order=i + 1,
        )

    logger.debug(f"Loaded {len(config.questions)} {phase}-quiz questions")


async def _load_exercise(lab: Lab, ex_dir: Path, max_points: float, sort_order: int) -> None:
    """Load an exercise from its directory."""
    ex_toml_path = ex_dir / 'exercise.toml'

    if not ex_toml_path.exists():
        logger.warning(f"Exercise config not found: {ex_toml_path}")
        return

    try:
        raw = toml.load(ex_toml_path)
        config = ExerciseConfig(**raw)
    except Exception as e:
        logger.error(f"Failed to load exercise {ex_dir}: {e}")
        return

    # Create exercise
    exercise = await Exercise.create(
        lab_id=lab.id,
        exercise_number=config.exercise.number,
        slug=ex_dir.name,
        title=config.exercise.title,
        objective=config.exercise.objective,
        max_points=max_points,
        sort_order=sort_order,
        instructions=load_markdown_file(ex_dir / config.files.instructions_file),
        prediction_prompt=load_markdown_file(ex_dir / config.files.prediction_file) if config.files.prediction_file else None,
        conclusion_prompt=load_markdown_file(ex_dir / config.files.conclusion_file) if config.files.conclusion_file else None,
    )

    # Load tasks
    for task_config in config.tasks:
        # Build type-specific config
        task_cfg = {}
        if task_config.columns:
            task_cfg['columns'] = [c.model_dump() for c in task_config.columns]
        if task_config.options:
            task_cfg['options'] = task_config.options
        if task_config.unit:
            task_cfg['unit'] = task_config.unit
        if task_config.min_value is not None:
            task_cfg['min_value'] = task_config.min_value
        if task_config.max_value is not None:
            task_cfg['max_value'] = task_config.max_value

        await ExerciseTask.create(
            exercise_id=exercise.id,
            task_number=task_config.number,
            task_type=task_config.type,
            prompt=task_config.prompt,
            sort_order=task_config.number,
            config=task_cfg if task_cfg else None,
        )

    logger.debug(f"Loaded exercise {config.exercise.number}: {config.exercise.title} "
                 f"({len(config.tasks)} tasks)")


async def reload_lab_content(lab_slug: str) -> Optional[Lab]:
    """Reload a specific lab's content from disk."""
    lab = await Lab.get_or_none(slug=lab_slug)

    if not lab or not lab.content_path:
        logger.error(f"Lab not found or no content path: {lab_slug}")
        return None

    lab_path = Path(lab.content_path)
    if not lab_path.exists():
        logger.error(f"Lab path no longer exists: {lab_path}")
        return None

    info = validate_lab_structure(lab_path)
    return await load_lab_content(info, force=True)


async def load_all_labs(labs_dir: Path, force: bool = False) -> dict:
    """Load all labs from a directory."""
    from .discovery import discover_labs

    results = {}
    discovered = discover_labs(labs_dir)

    for slug, info in discovered.items():
        if info.is_valid:
            results[slug] = await load_lab_content(info, force=force)
        else:
            results[slug] = None
            logger.error(f"Skipping invalid lab: {slug}")

    return results


async def load_all_labs_from_all_paths(
    include_bundled: bool = True,
    include_user: bool = True,
    force: bool = False
) -> dict:
    """
    Load all labs from all configured paths.

    Scans bundled labs first, then user labs. User labs can override
    bundled labs with the same slug.

    Args:
        include_bundled: Include bundled labs from novalabs/labs/
        include_user: Include user labs from ~/.novalabs/labs/
        force: Force reload even if content hash matches

    Returns:
        Dictionary mapping slug to Lab model (or None if invalid)
    """
    from .discovery import discover_all_labs

    results = {}
    discovered = discover_all_labs(
        include_bundled=include_bundled,
        include_user=include_user
    )

    for slug, info in discovered.items():
        if info.is_valid:
            results[slug] = await load_lab_content(info, force=force)
        else:
            results[slug] = None
            logger.error(f"Skipping invalid lab: {slug}")

    return results

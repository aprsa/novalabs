"""
Lab discovery and validation.

Scans lab directories for valid labs and validates their structure.
Supports multiple lab locations:
- Bundled labs: {package}/novalabs/labs/
- User labs: ~/.novalabs/labs/
"""

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict
import toml

from .schemas import LabConfig

logger = logging.getLogger(__name__)


# Default lab directory locations
def get_bundled_labs_dir() -> Path:
    """Get the path to bundled labs directory."""
    # Navigate from this file to novalabs/labs/
    return Path(__file__).parent.parent.parent / 'labs'


def get_user_labs_dir() -> Path:
    """Get the path to user-installed labs directory."""
    return Path.home() / '.novalabs' / 'labs'


def get_default_lab_paths() -> List[Path]:
    """
    Get the default lab directory paths in order of priority.

    Returns:
        List of paths: [bundled_labs_dir, user_labs_dir]
    """
    return [get_bundled_labs_dir(), get_user_labs_dir()]


@dataclass
class ValidationError:
    """A validation error found in lab content."""
    path: str
    message: str
    severity: str = "error"  # "error" or "warning"


@dataclass
class LabInfo:
    """Information about a discovered lab."""
    slug: str
    path: Path
    source: str = "unknown"  # "bundled" or "user"
    config: Optional[LabConfig] = None
    is_valid: bool = False
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    content_hash: Optional[str] = None


def compute_content_hash(lab_path: Path) -> str:
    """
    Compute a hash of all content files in a lab.

    Used to detect changes and avoid unnecessary reloading.
    """
    hasher = hashlib.sha256()

    content_dir = lab_path / 'content'
    if not content_dir.exists():
        return ""

    # Sort files for deterministic ordering
    for file_path in sorted(content_dir.rglob('*')):
        if file_path.is_file():
            # Include relative path in hash
            rel_path = file_path.relative_to(content_dir)
            hasher.update(str(rel_path).encode())
            hasher.update(file_path.read_bytes())

    return hasher.hexdigest()


def validate_lab_structure(lab_path: Path, source: str = "unknown") -> LabInfo:
    """
    Validate the structure of a lab directory.

    Checks for:
    - Required lab.toml file
    - Valid TOML syntax
    - Required fields in lab.toml
    - Referenced files exist (briefing, quizzes, exercises)

    Args:
        lab_path: Path to the lab directory
        source: Source identifier ("bundled" or "user")

    Returns:
        LabInfo with validation results
    """
    content_dir = lab_path / 'content'
    lab_toml_path = content_dir / 'lab.toml'

    # Initialize with slug from directory name
    info = LabInfo(
        slug=lab_path.name,
        path=lab_path,
        source=source,
    )

    # Check content directory exists
    if not content_dir.exists():
        info.errors.append(ValidationError(
            path=str(content_dir),
            message="Missing content/ directory"
        ))
        return info

    # Check lab.toml exists
    if not lab_toml_path.exists():
        info.errors.append(ValidationError(
            path=str(lab_toml_path),
            message="Missing lab.toml"
        ))
        return info

    # Parse lab.toml
    try:
        raw_config = toml.load(lab_toml_path)
    except toml.TomlDecodeError as e:
        info.errors.append(ValidationError(
            path=str(lab_toml_path),
            message=f"Invalid TOML syntax: {e}"
        ))
        return info

    # Validate against schema
    try:
        config = LabConfig(**raw_config)
        info.config = config
        info.slug = config.lab.slug
    except Exception as e:
        info.errors.append(ValidationError(
            path=str(lab_toml_path),
            message=f"Schema validation failed: {e}"
        ))
        return info

    # Check slug matches directory name
    if config.lab.slug != lab_path.name:
        info.warnings.append(ValidationError(
            path=str(lab_toml_path),
            message=f"Slug '{config.lab.slug}' doesn't match directory name '{lab_path.name}'",
            severity="warning"
        ))

    # Check briefing file exists
    briefing_path = content_dir / config.briefing.file
    if not briefing_path.exists():
        info.errors.append(ValidationError(
            path=str(briefing_path),
            message=f"Briefing file not found: {config.briefing.file}"
        ))

    # Check pre_quiz file exists
    pre_quiz_path = content_dir / config.pre_quiz.file
    if not pre_quiz_path.exists():
        info.errors.append(ValidationError(
            path=str(pre_quiz_path),
            message=f"Pre-quiz file not found: {config.pre_quiz.file}"
        ))

    # Check post_quiz file exists
    post_quiz_path = content_dir / config.post_quiz.file
    if not post_quiz_path.exists():
        info.errors.append(ValidationError(
            path=str(post_quiz_path),
            message=f"Post-quiz file not found: {config.post_quiz.file}"
        ))

    # Check exercise directories exist
    exercises_dir = content_dir / 'exercises'
    for ex_ref in config.exercises:
        ex_dir = exercises_dir / ex_ref.dir
        if not ex_dir.exists():
            info.errors.append(ValidationError(
                path=str(ex_dir),
                message=f"Exercise directory not found: {ex_ref.dir}"
            ))
            continue

        ex_toml = ex_dir / 'exercise.toml'
        if not ex_toml.exists():
            info.errors.append(ValidationError(
                path=str(ex_toml),
                message=f"Exercise config not found: {ex_ref.dir}/exercise.toml"
            ))

    # Set validity and compute hash
    info.is_valid = len(info.errors) == 0
    if info.is_valid:
        info.content_hash = compute_content_hash(lab_path)

    return info


def discover_labs(labs_dir: Path, source: str = "unknown") -> Dict[str, LabInfo]:
    """
    Discover all labs in a single directory.

    Scans for subdirectories containing content/lab.toml and validates each.

    Args:
        labs_dir: Path to the labs directory
        source: Source identifier for discovered labs

    Returns:
        Dictionary mapping lab slug to LabInfo
    """

    if not labs_dir.exists():
        logger.debug(f"Labs directory does not exist: {labs_dir}")
        return {}

    discovered = {}

    for item in labs_dir.iterdir():
        if not item.is_dir():
            continue

        # Skip directories starting with underscore or dot
        if item.name.startswith('_') or item.name.startswith('.'):
            continue

        # Check if this looks like a lab (has content/lab.toml)
        lab_toml = item / 'content' / 'lab.toml'
        if not lab_toml.exists():
            logger.debug(f"Skipping {item.name}: no content/lab.toml")
            continue

        # Validate the lab
        logger.info(f"Discovered lab: {item.name} (source: {source})")
        info = validate_lab_structure(item, source=source)

        if info.errors:
            for err in info.errors:
                logger.error(f"  {err.path}: {err.message}")
        if info.warnings:
            for warn in info.warnings:
                logger.warning(f"  {warn.path}: {warn.message}")

        discovered[info.slug] = info

    return discovered


def discover_all_labs(
    include_bundled: bool = True,
    include_user: bool = True,
    additional_paths: Optional[List[Path]] = None
) -> Dict[str, LabInfo]:
    """
    Discover labs from all configured locations.

    Labs are discovered in order:
    1. Bundled labs (novalabs/labs/)
    2. User labs (~/.novalabs/labs/)
    3. Additional paths (if provided)

    If a slug appears in multiple locations, later discoveries override
    earlier ones (user labs can override bundled labs).

    Args:
        include_bundled: Include bundled labs
        include_user: Include user-installed labs
        additional_paths: Additional directories to scan

    Returns:
        Dictionary mapping lab slug to LabInfo
    """
    all_labs: Dict[str, LabInfo] = {}

    # Discover bundled labs first
    if include_bundled:
        bundled_dir = get_bundled_labs_dir()
        if bundled_dir.exists():
            logger.info(f"Scanning bundled labs: {bundled_dir}")
            bundled = discover_labs(bundled_dir, source="bundled")
            all_labs.update(bundled)
            logger.info(f"Found {len(bundled)} bundled lab(s)")

    # Discover user labs (can override bundled)
    if include_user:
        user_dir = get_user_labs_dir()
        if user_dir.exists():
            logger.info(f"Scanning user labs: {user_dir}")
            user = discover_labs(user_dir, source="user")

            # Warn about overrides
            for slug in user:
                if slug in all_labs:
                    logger.warning(f"User lab '{slug}' overrides bundled lab")

            all_labs.update(user)
            logger.info(f"Found {len(user)} user lab(s)")

    # Discover from additional paths
    if additional_paths:
        for path in additional_paths:
            if path.exists():
                logger.info(f"Scanning additional path: {path}")
                additional = discover_labs(path, source=str(path))

                for slug in additional:
                    if slug in all_labs:
                        logger.warning(f"Lab '{slug}' from {path} overrides existing lab")

                all_labs.update(additional)

    return all_labs


def get_lab_info(lab_path: Path) -> LabInfo:
    """
    Get information about a specific lab.

    Args:
        lab_path: Path to the lab directory

    Returns:
        LabInfo with validation results
    """
    return validate_lab_structure(lab_path)


def ensure_user_labs_dir() -> Path:
    """
    Ensure the user labs directory exists.

    Returns:
        Path to user labs directory
    """
    user_dir = get_user_labs_dir()
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir

"""
Progress manager - handles overall lab progress and grading.

Manages the flow through lab phases:
1. NOT_STARTED → BRIEFING (start lab)
2. BRIEFING → PRE_QUIZ (finish reading)
3. PRE_QUIZ → EXERCISES (pass pre-quiz)
4. EXERCISES → POST_QUIZ (submit exercises)
5. POST_QUIZ → SUBMITTED (pass post-quiz)
6. SUBMITTED → GRADED (instructor grades)
"""

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Optional, List

from ..models import (
    Lab,
    Exercise,
    StudentLabProgress,
    StudentQuizAttempt,
    StudentExerciseResponse,
    LabStatus,
)


@dataclass
class LabProgressSummary:
    """Summary of student's progress through a lab."""
    lab_id: int
    lab_slug: str
    lab_title: str
    status: str

    # Phase completion
    briefing_complete: bool
    pre_quiz_passed: bool
    pre_quiz_attempts: int
    pre_quiz_points: float
    exercises_submitted: bool
    post_quiz_passed: bool
    post_quiz_attempts: int
    post_quiz_points: float

    # Exercise details
    exercises_started: int
    exercises_complete: int
    exercises_total: int

    # Grading
    exercise_points: Optional[float]
    exercise_max_points: float
    total_points: Optional[float]
    max_points: float
    grade_percentage: Optional[float]

    # Timestamps
    started_at: Optional[datetime]
    submitted_at: Optional[datetime]
    graded_at: Optional[datetime]


class ProgressManager:
    """
    Manages overall lab progress for a student.

    Usage:
        manager = await ProgressManager.create(user_id, lab_id)

        # Start the lab
        await manager.start_lab()

        # Complete briefing
        await manager.complete_briefing()

        # Get current status
        summary = await manager.get_summary()

        # For instructors: grade an exercise
        await manager.grade_exercise(exercise_id, points=18, notes="Good work!")
    """

    def __init__(self, user_id: int, lab_id: int, lab: Lab, progress: StudentLabProgress):
        """
        Private constructor - use create() instead.

        Args:
            user_id: Current user's ID
            lab_id: Current lab's ID
            lab: The Lab instance
            progress: The StudentLabProgress instance
        """
        self.user_id = user_id
        self.lab_id = lab_id
        self._lab = lab
        self._progress = progress

    @classmethod
    async def create(cls, user_id: int, lab_id: int) -> 'ProgressManager':
        """
        Factory method to create and initialize a ProgressManager.

        Args:
            user_id: Current user's ID
            lab_id: Current lab's ID

        Returns:
            Initialized ProgressManager instance
        """
        lab = await Lab.get(id=lab_id)
        progress = await cls._get_or_create_progress(user_id, lab_id)
        return cls(user_id, lab_id, lab, progress)

    @staticmethod
    async def _get_or_create_progress(user_id: int, lab_id: int) -> StudentLabProgress:
        """Get existing progress or create new."""
        progress = await StudentLabProgress.get_or_none(
            user_id=user_id,
            lab_id=lab_id,
        )

        if not progress:
            progress = await StudentLabProgress.create(
                user_id=user_id,
                lab_id=lab_id,
                status=LabStatus.NOT_STARTED,
            )

        return progress

    @property
    def status(self) -> str:
        """Get current status."""
        return self._progress.status

    async def start_lab(self) -> None:
        """Mark the lab as started (enter briefing phase)."""
        if self._progress.status == LabStatus.NOT_STARTED:
            self._progress.status = LabStatus.BRIEFING
            self._progress.started_at = datetime.now(UTC)
            await self._progress.save()

    async def complete_briefing(self) -> None:
        """Mark briefing as complete (ready for pre-quiz)."""
        if self._progress.status == LabStatus.BRIEFING:
            self._progress.status = LabStatus.PRE_QUIZ
            await self._progress.save()

    async def get_quiz_points(self, phase: str) -> tuple[float, int]:
        """
        Get total points and attempt count for a quiz phase.

        Returns:
            (total_points, attempt_count)
        """
        attempts = await StudentQuizAttempt.filter(
            progress_id=self._progress.id,
            phase=phase,
        )

        total_points = sum(a.points_earned for a in attempts)
        return total_points, len(attempts)

    async def has_passed_quiz(self, phase: str) -> bool:
        """Check if the student has passed the specified quiz."""
        attempt = await StudentQuizAttempt.get_or_none(
            progress_id=self._progress.id,
            phase=phase,
            passed=True,
        )
        return attempt is not None

    async def get_exercise_stats(self) -> dict:
        """Get exercise completion statistics."""
        exercises = await Exercise.filter(lab_id=self.lab_id)

        started = 0
        complete = 0
        graded_points = 0.0
        max_points = 0.0

        for ex in exercises:
            max_points += ex.max_points

            response = await StudentExerciseResponse.get_or_none(
                user_id=self.user_id,
                exercise_id=ex.id,
            )

            if response:
                started += 1
                if response.submitted_at:
                    complete += 1
                if response.grade is not None:
                    graded_points += response.grade

        return {
            'started': started,
            'complete': complete,
            'total': len(exercises),
            'graded_points': graded_points if complete > 0 else None,
            'max_points': max_points,
        }

    async def get_summary(self) -> LabProgressSummary:
        """Get a complete summary of progress."""
        pre_points, pre_attempts = await self.get_quiz_points('pre')
        post_points, post_attempts = await self.get_quiz_points('post')
        ex_stats = await self.get_exercise_stats()

        # Calculate totals
        max_points = (
            self._lab.pre_quiz_max_points +
            ex_stats['max_points'] +
            self._lab.post_quiz_max_points
        )

        total_points = None
        if self._progress.status == LabStatus.GRADED:
            total_points = pre_points + (ex_stats['graded_points'] or 0) + post_points

        grade_pct = None
        if total_points is not None and max_points > 0:
            grade_pct = (total_points / max_points) * 100

        return LabProgressSummary(
            lab_id=self.lab_id,
            lab_slug=self._lab.slug,
            lab_title=self._lab.title,
            status=self._progress.status,

            briefing_complete=self._progress.status not in [
                LabStatus.NOT_STARTED, LabStatus.BRIEFING
            ],
            pre_quiz_passed=await self.has_passed_quiz('pre'),
            pre_quiz_attempts=pre_attempts,
            pre_quiz_points=pre_points,
            exercises_submitted=self._progress.status in [
                LabStatus.POST_QUIZ, LabStatus.SUBMITTED, LabStatus.GRADED
            ],
            post_quiz_passed=await self.has_passed_quiz('post'),
            post_quiz_attempts=post_attempts,
            post_quiz_points=post_points,

            exercises_started=ex_stats['started'],
            exercises_complete=ex_stats['complete'],
            exercises_total=ex_stats['total'],

            exercise_points=ex_stats['graded_points'],
            exercise_max_points=ex_stats['max_points'],
            total_points=total_points,
            max_points=max_points,
            grade_percentage=grade_pct,

            started_at=self._progress.started_at,
            submitted_at=self._progress.submitted_at,
            graded_at=self._progress.graded_at,
        )

    # =========================================================================
    # Instructor Grading Methods
    # =========================================================================

    async def grade_exercise(
        self,
        exercise_id: int,
        points: float,
        notes: Optional[str] = None
    ) -> None:
        """Grade a student's exercise response."""
        exercise = await Exercise.get_or_none(id=exercise_id)
        if not exercise:
            raise ValueError(f"Exercise not found: {exercise_id}")

        if points < 0 or points > exercise.max_points:
            raise ValueError(
                f"Points must be between 0 and {exercise.max_points}"
            )

        response = await StudentExerciseResponse.get_or_none(
            user_id=self.user_id,
            exercise_id=exercise_id,
        )

        if response is None:
            raise ValueError(f"No response found for exercise {exercise_id}")

        response.grade = points
        response.grader_notes = notes  # type: ignore
        await response.save()

    async def finalize_grading(self, instructor_notes: Optional[str] = None) -> None:
        """Finalize grading for the lab."""
        exercises = await Exercise.filter(lab_id=self.lab_id)

        total_exercise_points = 0.0
        max_exercise_points = 0.0

        for ex in exercises:
            max_exercise_points += ex.max_points

            response = await StudentExerciseResponse.get_or_none(
                user_id=self.user_id,
                exercise_id=ex.id,
            )

            if response and response.grade is not None:
                total_exercise_points += response.grade

        # Calculate total grade
        pre_points, _ = await self.get_quiz_points('pre')
        post_points, _ = await self.get_quiz_points('post')

        total_grade = pre_points + total_exercise_points + post_points
        max_grade = (
            self._lab.pre_quiz_max_points +
            max_exercise_points +
            self._lab.post_quiz_max_points
        )

        # Update progress
        self._progress.grade = total_grade
        self._progress.max_grade = max_grade
        self._progress.instructor_notes = instructor_notes  # type: ignore
        self._progress.graded_at = datetime.now(UTC)
        self._progress.status = LabStatus.GRADED
        await self._progress.save()


# =============================================================================
# Utility Functions
# =============================================================================

async def get_lab_progress_for_user(user_id: int) -> List[LabProgressSummary]:
    """Get progress summaries for all labs for a user."""
    labs = await Lab.filter(is_active=True).order_by('sort_order')

    summaries = []
    for lab in labs:
        manager = await ProgressManager.create(user_id, lab.id)
        summaries.append(await manager.get_summary())

    return summaries


async def get_students_needing_grading(lab_id: int) -> List[StudentLabProgress]:
    """Get all students who have submitted but not been graded."""
    return await StudentLabProgress.filter(
        lab_id=lab_id,
        status=LabStatus.SUBMITTED,
    )

"""
Exercise manager - handles exercise operations and submission.

Students can:
- Complete exercises in any order
- Save partial progress
- Submit all exercises at once (locks further edits)
"""

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any

from ..models import (
    Lab,
    Exercise,
    ExerciseTask,
    StudentLabProgress,
    StudentExerciseResponse,
    StudentTaskResponse,
    LabStatus,
)


@dataclass
class ExerciseStatus:
    """Status of an individual exercise."""
    exercise_id: int
    exercise_number: int
    title: str
    is_started: bool
    has_prediction: bool
    has_conclusion: bool
    completed_tasks: int
    total_tasks: int
    is_complete: bool


@dataclass
class SubmissionWarning:
    """Warning about incomplete content."""
    exercise_number: int
    exercise_title: str
    message: str


class ExerciseManager:
    """
    Manages exercise operations for a student in a lab.

    Usage:
        manager = await ExerciseManager.create(user_id, lab_id)

        # Get all exercises
        exercises = await manager.get_exercises()

        # Save prediction
        await manager.save_prediction(exercise_id, "My prediction text")

        # Save task response
        await manager.save_task_response(task_id, {"rows": [[0, 42], ...]})

        # Check status
        statuses = await manager.get_all_status()

        # Submit all exercises
        warnings = await manager.submit_all()
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
    async def create(cls, user_id: int, lab_id: int) -> 'ExerciseManager':
        """
        Factory method to create and initialize an ExerciseManager.

        Args:
            user_id: Current user's ID
            lab_id: Current lab's ID

        Returns:
            Initialized ExerciseManager instance
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

    async def get_exercises(self) -> List[Exercise]:
        """Get all exercises for the lab in order."""
        exercises = await Exercise.filter(
            lab_id=self.lab_id
        ).order_by('sort_order')

        return list(exercises)

    async def get_exercise(self, exercise_id: int) -> Optional[Exercise]:
        """Get a specific exercise."""
        return await Exercise.get_or_none(id=exercise_id)

    async def get_tasks(self, exercise_id: int) -> List[ExerciseTask]:
        """Get all tasks for an exercise in order."""
        tasks = await ExerciseTask.filter(
            exercise_id=exercise_id
        ).order_by('sort_order')

        return list(tasks)

    async def _get_or_create_response(self, exercise_id: int) -> StudentExerciseResponse:
        """Get or create student response record for an exercise."""
        response = await StudentExerciseResponse.get_or_none(
            user_id=self.user_id,
            exercise_id=exercise_id,
        )

        if not response:
            response = await StudentExerciseResponse.create(
                user_id=self.user_id,
                exercise_id=exercise_id,
                started_at=datetime.now(UTC),
            )

        return response

    async def save_prediction(self, exercise_id: int, text: str) -> None:
        """Save the student's prediction for an exercise."""
        response = await self._get_or_create_response(exercise_id)
        response.prediction_text = text
        await response.save()

    async def save_conclusion(self, exercise_id: int, text: str) -> None:
        """Save the student's conclusion for an exercise."""
        response = await self._get_or_create_response(exercise_id)
        response.conclusion_text = text
        await response.save()

    async def save_task_response(self, task_id: int, data: Dict[str, Any]) -> None:
        """Save or update a task response."""
        # Get the task to find its exercise
        task = await ExerciseTask.get_or_none(id=task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        # Ensure exercise response exists
        ex_response = await self._get_or_create_response(task.exercise_id)  # type: ignore (dynamically added attribute by tortoise orm)

        # Find or create task response
        task_response = await StudentTaskResponse.get_or_none(
            exercise_response_id=ex_response.id,
            task_id=task_id,
        )

        if not task_response:
            task_response = StudentTaskResponse(
                exercise_response_id=ex_response.id,
                task_id=task_id,
            )

        task_response.response_data = data
        task_response.submitted_at = datetime.now(UTC)
        await task_response.save()

    async def get_response(self, exercise_id: int) -> Optional[StudentExerciseResponse]:
        """Get the student's response for an exercise."""
        return await StudentExerciseResponse.get_or_none(
            user_id=self.user_id,
            exercise_id=exercise_id,
        )

    async def get_task_response(self, task_id: int) -> Optional[StudentTaskResponse]:
        """Get the student's response for a specific task."""
        task = await ExerciseTask.get_or_none(id=task_id)
        if not task:
            return None

        ex_response = await self.get_response(task.exercise_id)  # type: ignore (dynamically added attribute by tortoise orm)
        if not ex_response:
            return None

        return await StudentTaskResponse.get_or_none(
            exercise_response_id=ex_response.id,
            task_id=task_id,
        )

    async def get_exercise_status(self, exercise_id: int) -> ExerciseStatus:
        """Get the completion status of an exercise."""
        exercise = await self.get_exercise(exercise_id)
        if not exercise:
            raise ValueError(f"Exercise not found: {exercise_id}")

        tasks = await self.get_tasks(exercise_id)
        response = await self.get_response(exercise_id)

        # Count completed tasks
        completed_tasks = 0
        if response:
            for task in tasks:
                task_response = await StudentTaskResponse.get_or_none(
                    exercise_response_id=response.id,
                    task_id=task.id,
                )
                if task_response and task_response.response_data:
                    completed_tasks += 1

        has_prediction = bool(response and response.prediction_text)
        has_conclusion = bool(response and response.conclusion_text)

        # Consider complete if all tasks filled and has prediction/conclusion
        is_complete = (
            completed_tasks == len(tasks) and
            (has_prediction or not exercise.prediction_prompt) and
            (has_conclusion or not exercise.conclusion_prompt)
        )

        return ExerciseStatus(
            exercise_id=exercise_id,
            exercise_number=exercise.exercise_number,
            title=exercise.title,
            is_started=response is not None,
            has_prediction=has_prediction,
            has_conclusion=has_conclusion,
            completed_tasks=completed_tasks,
            total_tasks=len(tasks),
            is_complete=is_complete,
        )

    async def get_all_status(self) -> List[ExerciseStatus]:
        """Get status for all exercises."""
        exercises = await self.get_exercises()
        statuses = []
        for ex in exercises:
            status = await self.get_exercise_status(ex.id)
            statuses.append(status)
        return statuses

    async def check_submission_warnings(self) -> List[SubmissionWarning]:
        """Check for incomplete content that would trigger warnings on submit."""
        warnings = []

        for status in await self.get_all_status():
            if not status.is_started:
                warnings.append(SubmissionWarning(
                    exercise_number=status.exercise_number,
                    exercise_title=status.title,
                    message="Exercise not started"
                ))
            elif not status.is_complete:
                missing = []
                if not status.has_prediction:
                    missing.append("prediction")
                if status.completed_tasks < status.total_tasks:
                    missing.append(f"{status.total_tasks - status.completed_tasks} task(s)")
                if not status.has_conclusion:
                    missing.append("conclusion")

                warnings.append(SubmissionWarning(
                    exercise_number=status.exercise_number,
                    exercise_title=status.title,
                    message=f"Missing: {', '.join(missing)}"
                ))

        return warnings

    async def submit_all(self, force: bool = False) -> List[SubmissionWarning]:
        """
        Submit all exercises for grading.

        Args:
            force: If True, submit even with warnings

        Returns:
            List of warnings (empty if submission successful or forced)
        """
        warnings = await self.check_submission_warnings()

        if warnings and not force:
            return warnings

        # Mark all exercise responses as submitted
        now = datetime.now(UTC)
        exercises = await self.get_exercises()

        for exercise in exercises:
            response = await self.get_response(exercise.id)
            if response:
                response.submitted_at = now
                await response.save()

        # Update progress status
        self._progress.status = LabStatus.POST_QUIZ
        await self._progress.save()

        return []

    async def is_submitted(self) -> bool:
        """Check if exercises have been submitted."""
        await self._progress.refresh_from_db()
        return self._progress.status in [
            LabStatus.POST_QUIZ,
            LabStatus.SUBMITTED,
            LabStatus.GRADED,
        ]

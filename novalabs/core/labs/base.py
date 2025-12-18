"""
Base class for NovaLabs lab logic.

BaseLab manages state, progress tracking, and provides lifecycle hooks
that can be overridden for custom lab behavior. It is decoupled from
the UI layer (BaseLabUI) to allow independent customization of logic
and presentation.

Usage:
    # Basic usage with default UI
    lab = BaseLab(user_id=123, lab=lab_model)
    await lab.init()

    # Custom logic (override hooks)
    class MyLab(BaseLab):
        async def on_exercise_enter(self, exercise_id: int) -> None:
            await super().on_exercise_enter(exercise_id)
            # Custom logic: load external resources, etc.
"""

from typing import List, TYPE_CHECKING

from ..models import Lab, Exercise
from ..managers import QuizManager, ExerciseManager, ProgressManager, TimeTracker

if TYPE_CHECKING:
    from ..managers.progress import LabProgressSummary
    from ..managers.exercise import ExerciseStatus
    from ..managers.quiz import QuizResult


class BaseLab:
    """
    Logic layer for NovaLabs labs.

    Manages state, progress, scoring, and provides lifecycle hooks.
    Designed to be composed with BaseLabUI (or custom UI classes).

    Attributes:
        user_id: Current user's ID
        lab: The Lab database model instance
        quiz_manager: Manages quiz operations
        exercise_manager: Manages exercise operations
        progress_manager: Manages overall progress
        time_tracker: Tracks time spent on segments
    """

    def __init__(self, user_id: int, lab: Lab):
        """
        Initialize the lab logic layer.

        Args:
            user_id: Current user's ID
            lab: The Lab model instance from database
        """
        self.user_id = user_id
        self.lab = lab

        # Managers (initialized in async init())
        self.quiz_manager: QuizManager
        self.exercise_manager: ExerciseManager
        self.progress_manager: ProgressManager
        self.time_tracker: TimeTracker

    async def init(self) -> 'BaseLab':
        """
        Async initialization to set up managers.

        Must be called after __init__ before using the lab.

        Returns:
            Self for method chaining
        """
        self.quiz_manager = await QuizManager.create(self.user_id, self.lab.id)
        self.exercise_manager = await ExerciseManager.create(self.user_id, self.lab.id)
        self.progress_manager = await ProgressManager.create(self.user_id, self.lab.id)
        self.time_tracker = TimeTracker(self.user_id, self.lab.id)

        return self

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def status(self) -> str:
        """Get current lab status."""
        return self.progress_manager.status

    async def get_exercises(self) -> List[Exercise]:
        """Get all exercises for this lab in order."""
        return await self.exercise_manager.get_exercises()

    async def get_progress_summary(self) -> 'LabProgressSummary':
        """Get a complete summary of student progress."""
        return await self.progress_manager.get_summary()

    async def get_exercise_statuses(self) -> List['ExerciseStatus']:
        """Get status for all exercises."""
        return await self.exercise_manager.get_all_status()

    # =========================================================================
    # Lifecycle Hooks
    #
    # Override these methods in subclasses for custom behavior.
    # Always call super() to ensure base functionality is preserved.
    # =========================================================================

    async def on_start(self) -> None:
        """
        Called when the lab is started.

        Default behavior: Mark lab as started, begin briefing time tracking.
        """
        await self.progress_manager.start_lab()
        await self.time_tracker.start_segment('briefing')

    async def on_briefing_complete(self) -> None:
        """
        Called when the student finishes reading the briefing.

        Default behavior: Stop briefing time tracking, update progress.
        """
        await self.time_tracker.stop_segment('briefing')
        await self.progress_manager.complete_briefing()

    async def on_quiz_start(self, phase: str, attempt_number: int) -> None:
        """
        Called when a quiz attempt starts.

        Args:
            phase: 'pre' or 'post'
            attempt_number: Which attempt this is (1-indexed)
        """
        await self.time_tracker.start_segment(
            f'{phase}_quiz',
            attempt_number=attempt_number
        )

    async def on_quiz_complete(self, phase: str, attempt_number: int) -> None:
        """
        Called when a quiz attempt is submitted.

        Args:
            phase: 'pre' or 'post'
            attempt_number: Which attempt this was (1-indexed)
        """
        await self.time_tracker.stop_segment(
            f'{phase}_quiz',
            attempt_number=attempt_number
        )

    async def on_exercise_enter(self, exercise_id: int) -> None:
        """
        Called when the student enters/starts working on an exercise.

        Args:
            exercise_id: Database ID of the exercise
        """
        await self.time_tracker.start_segment('exercise', segment_id=exercise_id)

    async def on_exercise_leave(self, exercise_id: int) -> None:
        """
        Called when the student leaves an exercise (navigates away).

        Args:
            exercise_id: Database ID of the exercise
        """
        await self.time_tracker.stop_segment('exercise', segment_id=exercise_id)

    async def on_exercises_submit(self) -> None:
        """
        Called when all exercises are submitted.

        Default behavior: Stop timing for all exercises, submit responses.
        """
        # Stop any active exercise timing
        for exercise in await self.get_exercises():
            await self.time_tracker.stop_segment('exercise', segment_id=exercise.id)

        # Submit all exercises
        await self.exercise_manager.submit_all(force=True)

    async def on_lab_complete(self) -> None:
        """
        Called when the lab is fully completed (post-quiz passed).

        Override to add custom completion logic (e.g., certificates,
        external notifications).
        """
        pass

    # =========================================================================
    # Quiz Operations
    # =========================================================================

    async def get_quiz_questions(self, phase: str):
        """
        Get quiz questions for the specified phase.

        Args:
            phase: 'pre' or 'post'

        Returns:
            List of Question objects
        """
        return await self.quiz_manager.get_questions(phase)

    async def get_quiz_attempt_number(self, phase: str) -> int:
        """
        Get the next attempt number for a quiz phase.

        Args:
            phase: 'pre' or 'post'

        Returns:
            Next attempt number (1 for first attempt)
        """
        return await self.quiz_manager.get_attempt_number(phase)

    async def submit_quiz_answers(
        self,
        phase: str,
        answers: List[int],
        questions=None
    ) -> 'QuizResult':
        """
        Submit quiz answers and get results.

        Args:
            phase: 'pre' or 'post'
            answers: List of selected option indices (0-based)
            questions: Optional list of questions (fetched if not provided)

        Returns:
            QuizResult with scoring details
        """
        return await self.quiz_manager.submit_answers(phase, answers, questions)

    async def has_passed_quiz(self, phase: str) -> bool:
        """
        Check if the student has passed a quiz phase.

        Args:
            phase: 'pre' or 'post'

        Returns:
            True if passed
        """
        return await self.quiz_manager.has_passed(phase)

    # =========================================================================
    # Exercise Operations
    # =========================================================================

    async def get_exercise_tasks(self, exercise_id: int):
        """
        Get all tasks for an exercise.

        Args:
            exercise_id: Database ID of the exercise

        Returns:
            List of ExerciseTask objects
        """
        return await self.exercise_manager.get_tasks(exercise_id)

    async def save_prediction(self, exercise_id: int, text: str) -> None:
        """
        Save the student's prediction for an exercise.

        Args:
            exercise_id: Database ID of the exercise
            text: Prediction text
        """
        await self.exercise_manager.save_prediction(exercise_id, text)

    async def save_conclusion(self, exercise_id: int, text: str) -> None:
        """
        Save the student's conclusion for an exercise.

        Args:
            exercise_id: Database ID of the exercise
            text: Conclusion text
        """
        await self.exercise_manager.save_conclusion(exercise_id, text)

    async def save_task_response(self, task_id: int, data: dict) -> None:
        """
        Save a task response.

        Args:
            task_id: Database ID of the task
            data: Response data (format depends on task type)
        """
        await self.exercise_manager.save_task_response(task_id, data)

    async def get_exercise_response(self, exercise_id: int):
        """
        Get the student's response for an exercise.

        Args:
            exercise_id: Database ID of the exercise

        Returns:
            StudentExerciseResponse or None
        """
        return await self.exercise_manager.get_response(exercise_id)

    async def get_task_response(self, task_id: int):
        """
        Get the student's response for a task.

        Args:
            task_id: Database ID of the task

        Returns:
            StudentTaskResponse or None
        """
        return await self.exercise_manager.get_task_response(task_id)

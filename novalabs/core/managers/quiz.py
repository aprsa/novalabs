"""
Quiz manager - handles quiz logic including scoring with attempt penalties.

Scoring rules:
- Each correct answer on 1st attempt: 1.0 point
- Each correct answer on 2nd attempt: 0.5 points
- Each correct answer on 3rd attempt: 0.25 points
- Each correct answer on 4th+ attempt: 0.25 points (floor)

Correct answers carry over between attempts. For example:
- 1st attempt: 6 correct → 6.0 points
- 2nd attempt: 3 more correct → 1.5 points
- Total: 7.5 points (for 9 correct answers)
"""

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import List, Optional

from ..models import (
    Lab,
    Question,
    StudentLabProgress,
    StudentQuizAttempt,
    LabStatus,
)


@dataclass
class QuizResult:
    """Result of scoring a quiz attempt."""
    score: int              # Number correct this attempt
    total: int              # Total questions
    passed: bool            # Score >= passing threshold
    points_earned: float    # Points for this attempt (with penalty)
    cumulative_points: float  # Total points across all attempts
    incorrect_indices: List[int]  # Which questions (0-indexed) were wrong
    attempt_number: int


class QuizManager:
    """
    Manages quiz operations for a student in a lab.

    Usage:
        manager = await QuizManager.create(user_id, lab_id)

        # Get questions for current attempt
        questions = await manager.get_questions('pre')

        # Submit answers and get results
        result = await manager.submit_answers('pre', [0, 1, 2, ...])

        # Check if passed
        if result.passed:
            # Proceed to exercises
    """

    # Points per correct answer by attempt number
    POINTS_BY_ATTEMPT = {
        1: 1.0,
        2: 0.5,
        3: 0.25,
    }
    DEFAULT_POINTS = 0.25  # 4th attempt and beyond

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
    async def create(cls, user_id: int, lab_id: int) -> 'QuizManager':
        """
        Factory method to create and initialize a QuizManager.

        Args:
            user_id: Current user's ID
            lab_id: Current lab's ID

        Returns:
            Initialized QuizManager instance
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

    async def get_questions(self, phase: str) -> List[Question]:
        """
        Get quiz questions for the specified phase.

        Args:
            phase: 'pre' or 'post'

        Returns:
            List of Question objects in order
        """
        questions = await Question.filter(
            lab_id=self.lab_id,
            phase=phase,
            is_active=True,
        ).order_by('sort_order')

        return list(questions)

    async def get_attempt_number(self, phase: str) -> int:
        """Get the next attempt number for this phase."""
        latest = await StudentQuizAttempt.filter(
            progress_id=self._progress.id,
            phase=phase,
        ).order_by('-attempt_number').first()

        return (latest.attempt_number + 1) if latest else 1

    async def get_previous_correct(self, phase: str) -> set:
        """
        Get question IDs that were answered correctly in previous attempts.

        Returns:
            Set of question IDs
        """
        attempts = await StudentQuizAttempt.filter(
            progress_id=self._progress.id,
            phase=phase,
        )

        correct_ids = set()
        for attempt in attempts:
            for answer in attempt.answers:
                if answer.get('correct', False):
                    correct_ids.add(answer['question_id'])

        return correct_ids

    async def get_cumulative_points(self, phase: str) -> float:
        """Get total points earned across all attempts."""
        attempts = await StudentQuizAttempt.filter(
            progress_id=self._progress.id,
            phase=phase,
        )

        return sum(a.points_earned for a in attempts)

    async def has_passed(self, phase: str) -> bool:
        """Check if the student has passed this quiz phase."""
        attempt = await StudentQuizAttempt.get_or_none(
            progress_id=self._progress.id,
            phase=phase,
            passed=True,
        )

        return attempt is not None

    async def submit_answers(
        self,
        phase: str,
        answers: list[int] | list[None],
        questions: Optional[List[Question]] = None
    ) -> QuizResult:
        """
        Submit quiz answers and record the attempt.

        Args:
            phase: 'pre' or 'post'
            answers: List of selected option indices (0-based)
            questions: Optional list of questions (if not provided, fetches from DB)

        Returns:
            QuizResult with scoring details
        """
        if questions is None:
            questions = await self.get_questions(phase)

        if len(answers) != len(questions):
            raise ValueError(
                f"Answer count ({len(answers)}) doesn't match "
                f"question count ({len(questions)})"
            )

        attempt_number = await self.get_attempt_number(phase)
        previously_correct = await self.get_previous_correct(phase)

        # Score the answers
        answer_records = []
        incorrect_indices = []
        new_correct_count = 0

        for i, (question, selected) in enumerate(zip(questions, answers)):
            is_correct = selected == question.correct_index
            was_previously_correct = question.id in previously_correct

            answer_records.append({
                'question_id': question.id,
                'selected_index': selected,
                'correct': is_correct,
            })

            if not is_correct:
                incorrect_indices.append(i)
            elif not was_previously_correct:
                # Newly correct this attempt
                new_correct_count += 1

        # Calculate points for newly correct answers
        points_per_answer = self.POINTS_BY_ATTEMPT.get(
            attempt_number, self.DEFAULT_POINTS
        )
        points_earned = new_correct_count * points_per_answer

        # Total correct (including previous attempts)
        total_correct = len(questions) - len(incorrect_indices)
        passed = total_correct >= self._lab.passing_score

        # Get cumulative points before this attempt
        prev_cumulative = await self.get_cumulative_points(phase)
        cumulative_points = prev_cumulative + points_earned

        # Record the attempt
        await StudentQuizAttempt.create(
            progress_id=self._progress.id,
            phase=phase,
            attempt_number=attempt_number,
            answers=answer_records,
            score=total_correct,
            total=len(questions),
            passed=passed,
            points_earned=points_earned,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        # Update progress status if passed
        if passed:
            if phase == 'pre':
                self._progress.status = LabStatus.EXERCISES
            elif phase == 'post':
                self._progress.status = LabStatus.SUBMITTED
            await self._progress.save()

        return QuizResult(
            score=total_correct,
            total=len(questions),
            passed=passed,
            points_earned=points_earned,
            cumulative_points=cumulative_points,
            incorrect_indices=incorrect_indices,
            attempt_number=attempt_number,
        )

    async def get_attempt_history(self, phase: str) -> List[StudentQuizAttempt]:
        """Get all attempts for this phase."""
        attempts = await StudentQuizAttempt.filter(
            progress_id=self._progress.id,
            phase=phase,
        ).order_by('attempt_number')

        return list(attempts)

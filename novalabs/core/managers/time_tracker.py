"""
Time tracker - tracks time spent on each segment of the lab.

Segments tracked:
- BRIEFING: Reading the mission briefing
- PRE_QUIZ: Taking the pre-quiz (per attempt)
- EXERCISE: Working on each exercise
- POST_QUIZ: Taking the post-quiz (per attempt)
"""

from datetime import datetime, UTC
from typing import Optional, List, Dict

from ..models import StudentTimeTracking, SegmentType


class TimeTracker:
    """
    Tracks time spent on lab segments.

    Usage:
        tracker = TimeTracker(user_id, lab_id)

        # Start timing a segment
        await tracker.start_segment('briefing')

        # ... student works ...

        # Stop timing
        duration = await tracker.stop_segment('briefing')

        # Get total time for a segment type
        total = await tracker.get_total_time('briefing')
    """

    def __init__(self, user_id: int, lab_id: int):
        """Initialize the time tracker."""
        self.user_id = user_id
        self.lab_id = lab_id

    async def start_segment(
        self,
        segment_type: str,
        segment_id: Optional[int] = None,
        attempt_number: Optional[int] = None
    ) -> StudentTimeTracking:
        """
        Start timing a segment.

        Args:
            segment_type: Type of segment (briefing, pre_quiz, exercise, post_quiz)
            segment_id: For exercises, the exercise_id
            attempt_number: For quizzes, the attempt number

        Returns:
            The created tracking record
        """
        # Check for existing active segment of same type
        existing = await self._get_active_segment(segment_type, segment_id, attempt_number)
        if existing:
            return existing

        tracking = await StudentTimeTracking.create(
            user_id=self.user_id,
            lab_id=self.lab_id,
            segment_type=segment_type,
            segment_id=segment_id,
            attempt_number=attempt_number,
        )

        return tracking

    async def stop_segment(
        self,
        segment_type: str,
        segment_id: Optional[int] = None,
        attempt_number: Optional[int] = None
    ) -> Optional[int]:
        """
        Stop timing a segment.

        Returns:
            Duration in seconds, or None if no active segment found
        """
        tracking = await self._get_active_segment(segment_type, segment_id, attempt_number)

        if not tracking:
            return None

        now = datetime.now(UTC)
        tracking.ended_at = now
        tracking.duration_seconds = int((now - tracking.started_at).total_seconds())
        await tracking.save()

        return tracking.duration_seconds

    async def _get_active_segment(
        self,
        segment_type: str,
        segment_id: Optional[int] = None,
        attempt_number: Optional[int] = None
    ) -> Optional[StudentTimeTracking]:
        """Get an active (not ended) tracking record."""
        filters = {
            'user_id': self.user_id,
            'lab_id': self.lab_id,
            'segment_type': segment_type,
            'ended_at': None,
        }

        if segment_id is not None:
            filters['segment_id'] = segment_id

        if attempt_number is not None:
            filters['attempt_number'] = attempt_number

        return await StudentTimeTracking.get_or_none(**filters)

    async def get_total_time(
        self,
        segment_type: str,
        segment_id: Optional[int] = None
    ) -> int:
        """
        Get total time spent on a segment type.

        Returns:
            Total seconds spent
        """
        filters = {
            'user_id': self.user_id,
            'lab_id': self.lab_id,
            'segment_type': segment_type,
            'duration_seconds__not': None,
        }

        if segment_id is not None:
            filters['segment_id'] = segment_id

        records = await StudentTimeTracking.filter(**filters)

        return sum(r.duration_seconds or 0 for r in records)

    async def get_all_times(self) -> Dict[str, int]:
        """Get total time for all segment types."""
        records = await StudentTimeTracking.filter(
            user_id=self.user_id,
            lab_id=self.lab_id,
            duration_seconds__not=None,
        )

        totals: Dict[str, int] = {}
        for record in records:
            key = record.segment_type
            totals[key] = totals.get(key, 0) + (record.duration_seconds or 0)

        return totals

    async def get_exercise_times(self) -> Dict[int, int]:
        """Get time spent on each exercise."""
        records = await StudentTimeTracking.filter(
            user_id=self.user_id,
            lab_id=self.lab_id,
            segment_type=SegmentType.EXERCISE,
            duration_seconds__not=None,
        )

        totals: Dict[int, int] = {}
        for record in records:
            if record.segment_id is not None:
                totals[record.segment_id] = (
                    totals.get(record.segment_id, 0) +
                    (record.duration_seconds or 0)
                )

        return totals

    async def get_lab_total_time(self) -> int:
        """Get total time spent on the entire lab."""
        totals = await self.get_all_times()
        return sum(totals.values())

    async def get_tracking_records(self) -> List[StudentTimeTracking]:
        """Get all tracking records for this user/lab."""
        return await StudentTimeTracking.filter(
            user_id=self.user_id,
            lab_id=self.lab_id,
        ).order_by('started_at')


def format_duration(seconds: int) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    remaining_seconds = seconds % 60

    if minutes < 60:
        if remaining_seconds > 0:
            return f"{minutes}m {remaining_seconds}s"
        return f"{minutes}m"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if remaining_minutes > 0:
        return f"{hours}h {remaining_minutes}m"
    return f"{hours}h"

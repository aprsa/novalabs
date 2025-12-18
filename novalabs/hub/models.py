"""
Tortoise ORM models for the NovaLabs hub.

User management and session storage.
"""

from enum import Enum
from tortoise import fields
from tortoise.models import Model

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from novalabs.core.models import StudentLabProgress, StudentExerciseResponse, StudentTimeTracking


class UserRole(str, Enum):
    STUDENT = 'student'
    TA = 'ta'
    INSTRUCTOR = 'instructor'
    ADMIN = 'admin'


class UserRank(str, Enum):
    DABBLER = 'dabbler'
    HOBBYIST = 'hobbyist'
    ENTHUSIAST = 'enthusiast'
    EXPLORER = 'explorer'
    APPRENTICE = 'apprentice'
    RESEARCHER = 'researcher'
    MASTER = 'master'


class User(Model):
    """Platform-wide user account."""
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=255, unique=True, index=True)
    hashed_password = fields.CharField(max_length=255)
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)
    role = fields.CharField(max_length=20, default=UserRole.STUDENT.value)
    institution = fields.CharField(max_length=200, null=True)
    is_active = fields.BooleanField(default=True)

    # Achievement tracking
    rank = fields.CharField(max_length=20, default=UserRank.DABBLER.value)
    total_score = fields.FloatField(default=0.0)
    total_bonus_points = fields.FloatField(default=0.0)

    created_at = fields.DatetimeField(auto_now_add=True)

    # Reverse relations
    sessions: fields.ReverseRelation['UserSession']
    progress_records: fields.ReverseRelation['CourseProgress']
    lab_progress: fields.ReverseRelation['StudentLabProgress']
    exercise_responses: fields.ReverseRelation['StudentExerciseResponse']
    time_tracking: fields.ReverseRelation['StudentTimeTracking']

    class Meta:  # type: ignore[misc]
        table = 'users'

    def __str__(self):
        return f"User({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class UserSession(Model):
    """Server-side session storage for UI state."""
    id = fields.IntField(pk=True)
    session_id = fields.CharField(max_length=64, unique=True, index=True)
    user = fields.ForeignKeyField('models.User', related_name='sessions')
    token = fields.TextField()

    # Session state (can store UI state, progress, etc.)
    state = fields.JSONField(null=True)

    # Metadata
    created_at = fields.DatetimeField(auto_now_add=True)
    last_activity = fields.DatetimeField(auto_now=True)
    expires_at = fields.DatetimeField()

    is_active = fields.BooleanField(default=True)

    class Meta:  # type: ignore[misc]
        table = 'user_sessions'

    def __str__(self):
        return f"Session({self.session_id[:8]}...)"


class ProgressStatus(str, Enum):
    LOCKED = 'locked'
    UNLOCKED = 'unlocked'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'


class CourseProgress(Model):
    """User progression through labs with scoring metadata."""

    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='progress_records')
    lab = fields.ForeignKeyField('models.Lab', related_name='course_progress')

    status = fields.CharField(max_length=20, default=ProgressStatus.LOCKED.value)
    score = fields.FloatField(null=True)
    bonus_points = fields.FloatField(default=0.0)
    attempts = fields.IntField(default=0)

    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)
    last_activity = fields.DatetimeField(null=True)

    instructor_notes = fields.TextField(null=True)
    score_overridden = fields.BooleanField(default=False)

    # Define _id fields for type checking
    user_id: int
    lab_id: int

    class Meta:  # type: ignore[misc]
        table = 'course_progress'
        unique_together = (('user', 'lab'),)

    def __str__(self) -> str:  # pragma: no cover - repr helper
        return f"Progress(user={self.user_id}, lab={self.lab_id}, {self.status})"

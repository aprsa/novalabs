"""
Tortoise ORM models for the NovaLabs lab framework.

Content Tables:
    - Lab: Lab metadata and configuration
    - Question: Quiz questions (pre and post)
    - Exercise: Exercise definitions
    - ExerciseTask: Individual tasks within exercises

Progress Tables:
    - StudentLabProgress: Overall lab progress per student
    - StudentQuizAttempt: Quiz attempt history
    - StudentExerciseResponse: Exercise predictions/conclusions
    - StudentTaskResponse: Individual task responses
    - StudentTimeTracking: Time spent per segment
"""

from enum import Enum
from tortoise import fields
from tortoise.models import Model

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from novalabs.hub.models import CourseProgress


# =============================================================================
# Enums
# =============================================================================

class LabStatus(str, Enum):
    """Overall lab progress status."""
    NOT_STARTED = 'not_started'
    BRIEFING = 'briefing'
    PRE_QUIZ = 'pre_quiz'
    EXERCISES = 'exercises'
    POST_QUIZ = 'post_quiz'
    SUBMITTED = 'submitted'
    GRADED = 'graded'


class QuizPhase(str, Enum):
    """Quiz phase identifier."""
    PRE = 'pre'
    POST = 'post'


class TaskType(str, Enum):
    """Exercise task types."""
    DATA_ENTRY = 'data_entry'
    SHORT_ANSWER = 'short_answer'
    LONG_ANSWER = 'long_answer'
    NUMERIC = 'numeric'
    SELECTION = 'selection'


class SegmentType(str, Enum):
    """Time tracking segment types."""
    BRIEFING = 'briefing'
    PRE_QUIZ = 'pre_quiz'
    EXERCISE = 'exercise'
    POST_QUIZ = 'post_quiz'


# =============================================================================
# Content Tables
# =============================================================================

class Lab(Model):
    """
    Lab definition loaded from content/lab.toml.

    Contains metadata and configuration for a lab module.
    """
    id = fields.IntField(pk=True)
    slug = fields.CharField(max_length=50, unique=True, index=True)
    title = fields.CharField(max_length=200)
    description = fields.TextField(null=True)
    version = fields.CharField(max_length=20, default='1.0.0')

    # Content
    briefing_content = fields.TextField(null=True)

    # Quiz configuration
    passing_score = fields.IntField(default=8)

    # Scoring
    pre_quiz_max_points = fields.FloatField(default=10.0)
    post_quiz_max_points = fields.FloatField(default=10.0)

    # Hub integration fields
    category = fields.CharField(max_length=100, default='General', null=True)
    prerequisite_refs = fields.JSONField(null=True)
    ui_url = fields.CharField(max_length=255, null=True)
    api_url = fields.CharField(max_length=255, null=True)
    session_manager_url = fields.CharField(max_length=255, null=True)
    has_bonus_challenge = fields.BooleanField(default=False)
    max_bonus_points = fields.FloatField(default=0.0)

    # Admin controls
    is_active = fields.BooleanField(default=True)
    sort_order = fields.IntField(default=0)

    # Content tracking
    content_hash = fields.CharField(max_length=64, null=True)
    content_path = fields.CharField(max_length=500, null=True)

    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # Reverse relations (defined by ForeignKey fields in other models)
    questions: fields.ReverseRelation['Question']
    exercises: fields.ReverseRelation['Exercise']
    student_progress: fields.ReverseRelation['StudentLabProgress']
    course_progress: fields.ReverseRelation['CourseProgress']

    class Meta:  # type: ignore[misc]
        table = 'labs'

    def __str__(self):
        return f"Lab({self.slug})"


class Question(Model):
    """
    Quiz question loaded from pre_quiz.toml or post_quiz.toml.
    """
    id = fields.IntField(pk=True)
    lab = fields.ForeignKeyField('models.Lab', related_name='questions')

    # Question type
    phase = fields.CharField(max_length=10)  # 'pre' or 'post'

    # Content
    question_text = fields.TextField()
    options = fields.JSONField(default=list)  # List of option strings
    correct_index = fields.IntField()

    # Ordering
    sort_order = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)

    class Meta:  # type: ignore[misc]
        table = 'questions'

    def __str__(self):
        return f"Question({self.id}, {self.phase})"


class Exercise(Model):
    """
    Exercise definition loaded from exercises/{slug}/exercise.toml.
    """
    id = fields.IntField(pk=True)
    lab = fields.ForeignKeyField('models.Lab', related_name='exercises')

    # Identification
    exercise_number = fields.IntField()
    slug = fields.CharField(max_length=50)
    title = fields.CharField(max_length=200)

    # Content (loaded from markdown files)
    objective = fields.TextField(null=True)
    instructions = fields.TextField(null=True)
    prediction_prompt = fields.TextField(null=True)
    conclusion_prompt = fields.TextField(null=True)

    # Scoring
    max_points = fields.FloatField(default=20.0)

    # Ordering
    sort_order = fields.IntField(default=0)

    # Reverse relations
    tasks: fields.ReverseRelation['ExerciseTask']
    student_responses: fields.ReverseRelation['StudentExerciseResponse']

    class Meta:  # type: ignore[misc]
        table = 'exercises'

    def __str__(self):
        return f"Exercise({self.exercise_number}, {self.title})"


class ExerciseTask(Model):
    """
    Individual task within an exercise.

    Tasks can be data entry tables, short answers, long answers, etc.
    """
    id = fields.IntField(pk=True)
    exercise = fields.ForeignKeyField('models.Exercise', related_name='tasks')

    # Identification
    task_number = fields.IntField()

    # Task definition
    task_type = fields.CharField(max_length=20)  # TaskType enum value
    prompt = fields.TextField()

    # Type-specific configuration
    # For data_entry: {columns: [{name, unit, editable, values}]}
    # For selection: {options: [...]}
    # For numeric: {unit: str, min: float, max: float}
    config = fields.JSONField(null=True)

    # Ordering
    sort_order = fields.IntField(default=0)

    # Reverse relations
    student_responses: fields.ReverseRelation['StudentTaskResponse']

    class Meta:  # type: ignore[misc]
        table = 'exercise_tasks'

    def __str__(self):
        return f"Task({self.task_number}, {self.task_type})"


# =============================================================================
# Student Progress Tables
# =============================================================================

class StudentLabProgress(Model):
    """
    Overall progress for a student through a lab.

    Tracks current phase, timestamps, and final grade.
    """
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='lab_progress')
    lab = fields.ForeignKeyField('models.Lab', related_name='student_progress')

    # Current progress
    status = fields.CharField(max_length=20, default=LabStatus.NOT_STARTED.value)

    # Timestamps
    started_at = fields.DatetimeField(null=True)
    submitted_at = fields.DatetimeField(null=True)
    graded_at = fields.DatetimeField(null=True)

    # Final grading (set by instructor)
    grade = fields.FloatField(null=True)
    max_grade = fields.FloatField(null=True)
    instructor_notes = fields.TextField(null=True)

    # Reverse relations
    quiz_attempts: fields.ReverseRelation['StudentQuizAttempt']

    # Define _id fields for type checking
    user_id: int
    lab_id: int

    class Meta:  # type: ignore[misc]
        table = 'student_lab_progress'
        unique_together = (('user', 'lab'),)

    def __str__(self):
        return f"Progress(user={self.user_id}, lab={self.lab_id}, {self.status})"


class StudentQuizAttempt(Model):
    """
    Record of a quiz attempt.

    Tracks which questions were shown, answers given, and score.
    """
    id = fields.IntField(pk=True)
    progress = fields.ForeignKeyField(
        'models.StudentLabProgress',
        related_name='quiz_attempts'
    )

    # Quiz identification
    phase = fields.CharField(max_length=10)  # 'pre' or 'post'
    attempt_number = fields.IntField()

    # Questions and answers
    # [{question_id: int, selected_index: int, correct: bool}, ...]
    answers = fields.JSONField(default=list)

    # Score
    score = fields.IntField()  # Number correct
    total = fields.IntField(default=10)
    passed = fields.BooleanField(default=False)

    # Points earned (accounting for attempt penalty)
    points_earned = fields.FloatField(default=0.0)

    # Timestamps
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)

    class Meta:  # type: ignore[misc]
        table = 'student_quiz_attempts'

    def __str__(self):
        return f"QuizAttempt({self.phase}, attempt={self.attempt_number})"


class StudentExerciseResponse(Model):
    """
    Student's response to an exercise (prediction and conclusion).

    Individual task responses are stored in StudentTaskResponse.
    """
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='exercise_responses')
    exercise = fields.ForeignKeyField(
        'models.Exercise',
        related_name='student_responses'
    )

    # Prediction (before observation)
    prediction_text = fields.TextField(null=True)

    # Conclusion (after observation)
    conclusion_text = fields.TextField(null=True)

    # Grading
    grade = fields.FloatField(null=True)
    grader_notes = fields.TextField(null=True)
    grader_notes: str | None

    # Timestamps
    started_at = fields.DatetimeField(null=True)
    submitted_at = fields.DatetimeField(null=True)

    # Reverse relations
    task_responses: fields.ReverseRelation['StudentTaskResponse']

    # Define _id fields for type checking
    user_id: int
    exercise_id: int

    class Meta:  # type: ignore[misc]
        table = 'student_exercise_responses'
        unique_together = (('user', 'exercise'),)

    def __str__(self):
        return f"ExerciseResponse(user={self.user_id}, ex={self.exercise_id})"


class StudentTaskResponse(Model):
    """
    Student's response to an individual task.

    Response format depends on task_type:
    - data_entry: {rows: [[val1, val2, ...], ...]}
    - short_answer: {text: str}
    - long_answer: {text: str}
    - numeric: {value: float}
    - selection: {selected_index: int}
    """
    id = fields.IntField(pk=True)
    exercise_response = fields.ForeignKeyField(
        'models.StudentExerciseResponse',
        related_name='task_responses'
    )
    task = fields.ForeignKeyField(
        'models.ExerciseTask',
        related_name='student_responses'
    )

    # Response data (format depends on task type)
    response_data = fields.JSONField(default=dict)

    # Timestamps
    submitted_at = fields.DatetimeField(null=True)

    # Define _id fields for type checking
    exercise_response_id: int
    task_id: int

    class Meta:  # type: ignore[misc]
        table = 'student_task_responses'

    def __str__(self):
        return f"TaskResponse(task={self.task_id})"


class StudentTimeTracking(Model):
    """
    Time spent on each segment of the lab.
    """
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='time_tracking')
    lab = fields.ForeignKeyField('models.Lab', related_name='time_tracking')

    # Segment identification
    segment_type = fields.CharField(max_length=20)  # SegmentType enum value
    segment_id = fields.IntField(null=True)  # exercise_id when segment_type='exercise'

    # For quizzes, track attempt number
    attempt_number = fields.IntField(null=True)

    # Timing
    started_at = fields.DatetimeField(auto_now_add=True)
    ended_at = fields.DatetimeField(null=True)
    duration_seconds = fields.IntField(null=True)

    class Meta:  # type: ignore[misc]
        table = 'student_time_tracking'

    def __str__(self):
        return f"TimeTracking({self.segment_type}, {self.duration_seconds}s)"


# =============================================================================
# Admin Tables
# =============================================================================

class AdminNotification(Model):
    """
    Notifications for administrators about errors and important events.
    
    Used to track runtime errors, validation issues, and other events
    that administrators should be aware of.
    """
    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    
    # Severity level
    severity = fields.CharField(max_length=20)  # 'error', 'warning', 'info'
    
    # Notification content
    title = fields.CharField(max_length=200)
    message = fields.TextField()
    traceback = fields.TextField(null=True)
    
    # Context (optional)
    lab_id = fields.IntField(null=True)
    user_id = fields.IntField(null=True)
    
    # Status
    is_read = fields.BooleanField(default=False)
    read_at = fields.DatetimeField(null=True)
    read_by_user_id = fields.IntField(null=True)
    
    # Admin notes (for tracking what was done about the issue)
    admin_notes = fields.TextField(null=True)

    class Meta:  # type: ignore[misc]
        table = 'admin_notifications'

    def __str__(self):
        return f"AdminNotification({self.severity}: {self.title})"

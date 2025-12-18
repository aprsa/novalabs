"""
NovaLabs Core - Lab Framework

A framework for building interactive astronomy labs with:
- Structured content (briefings, quizzes, exercises)
- Progress tracking
- Time tracking
- Grading support

Usage:
    from novalabs.core import BaseLab, QuizManager, ExerciseManager
    from novalabs.core.models import Lab, Exercise, Question
"""

from .models import (
    Lab,
    Question,
    Exercise,
    ExerciseTask,
    StudentLabProgress,
    StudentQuizAttempt,
    StudentExerciseResponse,
    StudentTaskResponse,
    StudentTimeTracking,
    AdminNotification,
    LabStatus,
    QuizPhase,
    TaskType,
)

__all__ = [
    # Models
    'Lab',
    'Question',
    'Exercise',
    'ExerciseTask',
    'StudentLabProgress',
    'StudentQuizAttempt',
    'StudentExerciseResponse',
    'StudentTaskResponse',
    'StudentTimeTracking',
    'AdminNotification',
    # Enums
    'LabStatus',
    'QuizPhase',
    'TaskType',
]

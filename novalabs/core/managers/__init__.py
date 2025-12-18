"""
Business logic managers for NovaLabs labs.

These managers provide the API between the UI and database,
encapsulating all business logic for quizzes, exercises, and progress tracking.
"""

from .quiz import QuizManager
from .exercise import ExerciseManager
from .progress import ProgressManager
from .time_tracker import TimeTracker

__all__ = [
    'QuizManager',
    'ExerciseManager',
    'ProgressManager',
    'TimeTracker',
]

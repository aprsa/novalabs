from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, UTC
from enum import Enum


class UserRole(str, Enum):
    STUDENT = 'student'
    TA = 'ta'
    INSTRUCTOR = 'instructor'
    ADMIN = 'admin'


class UserRank(str, Enum):
    """Student progression ranks - casual to expert"""
    DABBLER = 'dabbler'                  # Starting rank (0%)
    HOBBYIST = 'hobbyist'                # 15% progress
    ENTHUSIAST = 'enthusiast'            # 30% progress
    EXPLORER = 'explorer'                # 45% progress
    APPRENTICE = 'apprentice'            # 60% progress
    RESEARCHER = 'researcher'            # 75% progress
    MASTER = 'master'                    # 90%+ progress


class ProgressStatus(str, Enum):
    """Lab progress states"""
    LOCKED = 'locked'               # Prerequisites not met
    UNLOCKED = 'unlocked'           # Can start
    IN_PROGRESS = 'in_progress'     # Started but not completed
    COMPLETED = 'completed'         # Finished with score


class User(SQLModel, table=True):
    """Platform-wide user account"""
    __tablename__ = 'users'

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    first_name: str
    last_name: str
    role: str = Field(default=UserRole.STUDENT)
    institution: Optional[str] = None
    is_active: bool = Field(default=True)

    # Achievement tracking
    rank: str = Field(default=UserRank.DABBLER)
    total_score: float = Field(default=0.0)      # Sum of all lab scores
    total_bonus_points: float = Field(default=0.0)  # Extra challenges

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    progress: List['UserProgress'] = Relationship(back_populates='user')


class Lab(SQLModel, table=True):
    """Lab module"""
    __tablename__ = 'labs'

    id: Optional[int] = Field(default=None, primary_key=True)
    ref: str = Field(unique=True, index=True)  # celestial_nav, phoebe, exoplanets
    name: str                                    # "Celestial Navigation"
    description: str

    # Sequence control
    sequence_order: int = Field(index=True)     # 1, 2, 3... (determines unlock order)
    category: str                                # "Earth", "Solar System", "Stars"
    prerequisite_refs: Optional[str] = None     # JSON array: '["roemer_delay", "eclipses"]'

    # Standalone lab interface
    ui_url: str                                  # http://localhost:8012

    # Scoring
    max_score: float = Field(default=100.0)     # Maximum possible score
    has_bonus_challenge: bool = Field(default=False)  # Extra points available?
    max_bonus_points: float = Field(default=0.0)      # Max bonus if has_bonus_challenge

    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    progress: List['UserProgress'] = Relationship(back_populates='lab')


class UserProgress(SQLModel, table=True):
    """
    Student progress through a specific lab

    Tracks completion status, scores, attempts, and timestamps.
    """
    __tablename__ = 'user_progress'

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key='users.id', index=True)
    lab_id: int = Field(foreign_key='labs.id', index=True)

    # Progress state
    status: str = Field(default=ProgressStatus.LOCKED)  # locked/unlocked/in_progress/completed

    # Scoring
    score: Optional[float] = None               # 0-100 score for main lab
    bonus_points: float = Field(default=0.0)    # Extra points from bonus challenges

    # Activity tracking
    attempts: int = Field(default=0)            # Number of times started
    started_at: Optional[datetime] = None       # First attempt timestamp
    completed_at: Optional[datetime] = None     # Completion timestamp
    last_activity: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Optional instructor feedback
    instructor_notes: Optional[str] = None
    score_overridden: bool = Field(default=False)  # True if admin manually set score

    # Relationships
    user: User = Relationship(back_populates='progress')
    lab: Lab = Relationship(back_populates='progress')

    class Config:
        # Ensure unique constraint on user+lab combination
        table_args = {'sqlite_autoincrement': True}


class UserSession(SQLModel, table=True):
    """Server-side session storage for UI state"""
    __tablename__ = 'user_sessions'

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(unique=True, index=True)  # Unique session identifier
    user_id: int = Field(foreign_key='users.id', index=True)
    token: str  # JWT token

    # Session state (can store UI state, progress, etc.)
    state: Optional[str] = None  # JSON blob for arbitrary state

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime  # Session expiration

    is_active: bool = Field(default=True)


# Future enhancement: Achievement/Badge system
# class Achievement(SQLModel, table=True):
#     """Achievements/badges that users can earn"""
#     __tablename__ = 'achievements'
#
#     id: Optional[int] = Field(default=None, primary_key=True)
#     ref: str = Field(unique=True)
#     name: str
#     description: str
#     icon: str  # Icon name or emoji
#     criteria: str  # JSON describing how to earn it


# class UserAchievement(SQLModel, table=True):
#     """Junction table for user achievements"""
#     __tablename__ = 'user_achievements'
#
#     id: Optional[int] = Field(default=None, primary_key=True)
#     user_id: int = Field(foreign_key='users.id')
#     achievement_id: int = Field(foreign_key='achievements.id')
#     earned_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

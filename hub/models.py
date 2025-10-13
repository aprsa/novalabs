from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, UTC
from enum import Enum


class UserRole(str, Enum):
    STUDENT = 'student'
    INSTRUCTOR = 'instructor'
    TA = 'ta'
    ADMIN = 'admin'


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    enrollments: List['Enrollment'] = Relationship(back_populates='user')
    lab_sessions: List['LabSession'] = Relationship(back_populates='user')


class Course(SQLModel, table=True):
    """A course (e.g., ASTR 101, Fall 2024)"""
    __tablename__ = 'courses'

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str                          # ASTR-101
    name: str                          # Introduction to Astronomy
    semester: str                      # Fall 2024
    instructor_id: int = Field(foreign_key='users.id')
    ta_id: Optional[int] = Field(foreign_key='users.id', default=None)
    institution: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    enrollments: List['Enrollment'] = Relationship(back_populates='course')
    assignments: List['LabAssignment'] = Relationship(back_populates='course')


class Enrollment(SQLModel, table=True):
    """Student enrollment in a course"""
    __tablename__ = 'enrollments'

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key='users.id')
    course_id: int = Field(foreign_key='courses.id')
    role: str = Field(default=UserRole.STUDENT)  # student, ta, instructor
    enrolled_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    user: User = Relationship(back_populates='enrollments')
    course: Course = Relationship(back_populates='enrollments')


class Lab(SQLModel, table=True):
    """A lab module (e.g., PHOEBE Lab, Exoplanet Lab)"""
    __tablename__ = 'labs'

    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)  # phoebe, exoplanet
    name: str                                    # PHOEBE Binary Star Lab
    description: str
    ui_url: str                                  # http://localhost:8012
    api_url: str                                 # http://localhost:8010
    session_manager_url: str                     # http://localhost:8011
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    assignments: List['LabAssignment'] = Relationship(back_populates='lab')
    sessions: List['LabSession'] = Relationship(back_populates='lab')


class LabAssignment(SQLModel, table=True):
    """Assignment of a lab to a course"""
    __tablename__ = 'lab_assignments'

    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key='courses.id')
    lab_id: int = Field(foreign_key='labs.id')
    title: str                                   # "Lab 1: Binary Star Basics"
    due_date: Optional[datetime] = None
    points_possible: Optional[float] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    course: Course = Relationship(back_populates='assignments')
    lab: Lab = Relationship(back_populates='assignments')
    grades: List['Grade'] = Relationship(back_populates='assignment')


class LabSession(SQLModel, table=True):
    """Student's session in a specific lab"""
    __tablename__ = "lab_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key='users.id')
    lab_id: int = Field(foreign_key='labs.id')
    course_id: Optional[int] = Field(foreign_key='courses.id')
    assignment_id: Optional[int] = Field(foreign_key='lab_assignments.id')

    # Lab-specific session info
    external_session_id: str           # ID from lab's session manager

    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None

    # Relationships
    user: User = Relationship(back_populates='lab_sessions')
    lab: Lab = Relationship(back_populates='sessions')


class Grade(SQLModel, table=True):
    """Grade for a lab assignment"""
    __tablename__ = 'grades'

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key='users.id')
    assignment_id: int = Field(foreign_key='lab_assignments.id')
    score: Optional[float] = None
    max_score: float
    graded_at: Optional[datetime] = None
    graded_by: Optional[int] = Field(foreign_key='users.id')
    feedback: Optional[str] = None
    auto_graded: bool = Field(default=False)

    # Relationships
    assignment: LabAssignment = Relationship(back_populates='grades')

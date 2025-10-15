from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from ..database import get_session
from ..models import Course, User
from ..dependencies import get_current_user

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get('', response_model=List[dict])
def get_courses(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """Get all available courses"""
    courses = session.exec(select(Course).where(Course.is_active)).all()
    return [
        {
            "id": course.id,
            "code": course.code,
            "name": course.name,
            "semester": course.semester,
            "instructor_id": course.instructor_id,
            "ta_id": course.ta_id,
            "institution": course.institution,
            "is_active": course.is_active,
            "created_at": course.created_at.isoformat()
        }
        for course in courses
    ]


@router.post('', response_model=dict)
def create_course(
    course_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new course (instructor/admin only)"""
    # Check if user is instructor or admin
    if current_user.role not in ['instructor', 'admin']:
        raise HTTPException(status_code=403, detail="Instructor or admin privileges required")

    # Check if instructor exists
    instructor = session.get(User, course_data['instructor_id'])
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")

    # Check if TA exists (if provided)
    if course_data.get('ta_id'):
        ta = session.get(User, course_data['ta_id'])
        if not ta:
            raise HTTPException(status_code=404, detail="TA not found")

    # Create course
    course = Course(
        code=course_data['code'],
        name=course_data['name'],
        semester=course_data['semester'],
        instructor_id=course_data['instructor_id'],
        ta_id=course_data.get('ta_id'),
        institution=course_data.get('institution'),
        is_active=course_data.get('is_active', True)
    )

    session.add(course)
    session.commit()
    session.refresh(course)

    return {
        "id": course.id,
        "code": course.code,
        "name": course.name,
        "semester": course.semester,
        "instructor_id": course.instructor_id,
        "ta_id": course.ta_id,
        "institution": course.institution,
        "is_active": course.is_active,
        "created_at": course.created_at.isoformat()
    }


@router.get('/{course_id}', response_model=dict)
def get_course(
    course_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get course by ID"""
    course = session.get(Course, course_id)
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return {
        "id": course.id,
        "code": course.code,
        "name": course.name,
        "semester": course.semester,
        "instructor_id": course.instructor_id,
        "ta_id": course.ta_id,
        "institution": course.institution,
        "is_active": course.is_active,
        "created_at": course.created_at.isoformat()
    }

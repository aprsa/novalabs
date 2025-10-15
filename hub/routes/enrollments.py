from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from ..database import get_session
from ..models import Enrollment, User, Course
from ..dependencies import get_current_user

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.get('', response_model=List[dict])
def get_enrollments(
    course_id: int = None,
    user_id: int = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get enrollments, optionally filtered by course_id or user_id"""
    query = select(Enrollment)
    
    if course_id is not None:
        query = query.where(Enrollment.course_id == course_id)
    if user_id is not None:
        query = query.where(Enrollment.user_id == user_id)
    
    enrollments = session.exec(query).all()
    
    result = []
    for enrollment in enrollments:
        # Fetch related user and course for display
        user = session.get(User, enrollment.user_id)
        course = session.get(Course, enrollment.course_id)
        
        result.append({
            "id": enrollment.id,
            "user_id": enrollment.user_id,
            "course_id": enrollment.course_id,
            "role": enrollment.role,
            "enrolled_at": enrollment.enrolled_at.isoformat(),
            "user": {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name
            } if user else None,
            "course": {
                "code": course.code,
                "name": course.name,
                "semester": course.semester
            } if course else None
        })
    
    return result


@router.post('', response_model=dict)
def create_enrollment(
    enrollment_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new enrollment (instructor/admin only)"""
    # Check if user is instructor or admin
    if current_user.role not in ['instructor', 'admin']:
        raise HTTPException(status_code=403, detail="Instructor or admin privileges required")
    
    # Check if user exists
    user = session.get(User, enrollment_data['user_id'])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if course exists
    course = session.get(Course, enrollment_data['course_id'])
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if enrollment already exists
    existing = session.exec(
        select(Enrollment).where(
            Enrollment.user_id == enrollment_data['user_id'],
            Enrollment.course_id == enrollment_data['course_id']
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="User is already enrolled in this course")
    
    # Create enrollment
    enrollment = Enrollment(
        user_id=enrollment_data['user_id'],
        course_id=enrollment_data['course_id'],
        role=enrollment_data.get('role', 'student')
    )
    
    session.add(enrollment)
    session.commit()
    session.refresh(enrollment)
    
    return {
        "id": enrollment.id,
        "user_id": enrollment.user_id,
        "course_id": enrollment.course_id,
        "role": enrollment.role,
        "enrolled_at": enrollment.enrolled_at.isoformat(),
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name
        },
        "course": {
            "code": course.code,
            "name": course.name,
            "semester": course.semester
        }
    }


@router.get('/{enrollment_id}', response_model=dict)
def get_enrollment(
    enrollment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get enrollment by ID"""
    enrollment = session.get(Enrollment, enrollment_id)
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    user = session.get(User, enrollment.user_id)
    course = session.get(Course, enrollment.course_id)
    
    return {
        "id": enrollment.id,
        "user_id": enrollment.user_id,
        "course_id": enrollment.course_id,
        "role": enrollment.role,
        "enrolled_at": enrollment.enrolled_at.isoformat(),
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name
        } if user else None,
        "course": {
            "code": course.code,
            "name": course.name,
            "semester": course.semester
        } if course else None
    }


@router.delete('/{enrollment_id}')
def delete_enrollment(
    enrollment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete an enrollment (instructor/admin only)"""
    # Check if user is instructor or admin
    if current_user.role not in ['instructor', 'admin']:
        raise HTTPException(status_code=403, detail="Instructor or admin privileges required")
    
    enrollment = session.get(Enrollment, enrollment_id)
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    session.delete(enrollment)
    session.commit()
    
    return {"status": "deleted", "id": enrollment_id}

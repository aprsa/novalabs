from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from datetime import datetime, UTC

from ..database import get_session
from ..models import LabSession, User, Lab, Course
from ..dependencies import get_current_user

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get('', response_model=List[dict])
def get_sessions(
    user_id: int = None,
    lab_id: int = None,
    course_id: int = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get lab sessions, optionally filtered by user_id, lab_id, or course_id"""
    query = select(LabSession)
    
    if user_id is not None:
        query = query.where(LabSession.user_id == user_id)
    if lab_id is not None:
        query = query.where(LabSession.lab_id == lab_id)
    if course_id is not None:
        query = query.where(LabSession.course_id == course_id)
    
    lab_sessions = session.exec(query).all()
    
    result = []
    for lab_session in lab_sessions:
        # Fetch related user, lab, and course for display
        user = session.get(User, lab_session.user_id)
        lab = session.get(Lab, lab_session.lab_id)
        course = session.get(Course, lab_session.course_id) if lab_session.course_id else None
        
        result.append({
            "id": lab_session.id,
            "user_id": lab_session.user_id,
            "lab_id": lab_session.lab_id,
            "course_id": lab_session.course_id,
            "assignment_id": lab_session.assignment_id,
            "external_session_id": lab_session.external_session_id,
            "started_at": lab_session.started_at.isoformat(),
            "last_activity": lab_session.last_activity.isoformat(),
            "completed_at": lab_session.completed_at.isoformat() if lab_session.completed_at else None,
            "user": {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name
            } if user else None,
            "lab": {
                "slug": lab.slug,
                "name": lab.name
            } if lab else None,
            "course": {
                "code": course.code,
                "name": course.name,
                "semester": course.semester
            } if course else None
        })
    
    return result


@router.post('', response_model=dict)
def create_session(
    session_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new lab session"""
    # Check if user exists
    user = session.get(User, session_data['user_id'])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if lab exists
    lab = session.get(Lab, session_data['lab_id'])
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    
    # If course_id provided, verify it exists
    course = None
    if 'course_id' in session_data and session_data['course_id']:
        course = session.get(Course, session_data['course_id'])
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
    
    # Generate external session ID (in real implementation, this would call lab's session manager)
    import uuid
    external_session_id = session_data.get('external_session_id', str(uuid.uuid4()))
    
    # Create session
    lab_session = LabSession(
        user_id=session_data['user_id'],
        lab_id=session_data['lab_id'],
        course_id=session_data.get('course_id'),
        assignment_id=session_data.get('assignment_id'),
        external_session_id=external_session_id
    )
    
    session.add(lab_session)
    session.commit()
    session.refresh(lab_session)
    
    return {
        "id": lab_session.id,
        "user_id": lab_session.user_id,
        "lab_id": lab_session.lab_id,
        "course_id": lab_session.course_id,
        "assignment_id": lab_session.assignment_id,
        "external_session_id": lab_session.external_session_id,
        "started_at": lab_session.started_at.isoformat(),
        "last_activity": lab_session.last_activity.isoformat(),
        "completed_at": lab_session.completed_at.isoformat() if lab_session.completed_at else None,
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name
        },
        "lab": {
            "slug": lab.slug,
            "name": lab.name
        },
        "course": {
            "code": course.code,
            "name": course.name,
            "semester": course.semester
        } if course else None
    }


@router.get('/{session_id}', response_model=dict)
def get_session(
    session_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get session by ID"""
    lab_session = session.get(LabSession, session_id)
    
    if not lab_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    user = session.get(User, lab_session.user_id)
    lab = session.get(Lab, lab_session.lab_id)
    course = session.get(Course, lab_session.course_id) if lab_session.course_id else None
    
    return {
        "id": lab_session.id,
        "user_id": lab_session.user_id,
        "lab_id": lab_session.lab_id,
        "course_id": lab_session.course_id,
        "assignment_id": lab_session.assignment_id,
        "external_session_id": lab_session.external_session_id,
        "started_at": lab_session.started_at.isoformat(),
        "last_activity": lab_session.last_activity.isoformat(),
        "completed_at": lab_session.completed_at.isoformat() if lab_session.completed_at else None,
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name
        } if user else None,
        "lab": {
            "slug": lab.slug,
            "name": lab.name
        } if lab else None,
        "course": {
            "code": course.code,
            "name": course.name,
            "semester": course.semester
        } if course else None
    }


@router.patch('/{session_id}/activity', response_model=dict)
def update_session_activity(
    session_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update last activity timestamp for a session"""
    lab_session = session.get(LabSession, session_id)
    
    if not lab_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    lab_session.last_activity = datetime.now(UTC)
    
    session.add(lab_session)
    session.commit()
    session.refresh(lab_session)
    
    return {
        "id": lab_session.id,
        "last_activity": lab_session.last_activity.isoformat(),
        "status": "updated"
    }


@router.post('/{session_id}/complete', response_model=dict)
def complete_session(
    session_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Mark a lab session as completed"""
    lab_session = session.get(LabSession, session_id)
    
    if not lab_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if lab_session.completed_at:
        raise HTTPException(status_code=400, detail="Session already completed")
    
    lab_session.completed_at = datetime.now(UTC)
    lab_session.last_activity = datetime.now(UTC)
    
    session.add(lab_session)
    session.commit()
    session.refresh(lab_session)
    
    return {
        "id": lab_session.id,
        "completed_at": lab_session.completed_at.isoformat(),
        "status": "completed"
    }

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from ..database import get_session
from ..models import Lab, LabAssignment, User, Enrollment
from ..dependencies import get_current_user

router = APIRouter(prefix="/labs", tags=["labs"])


@router.get('', response_model=List[dict])
def get_labs(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """Get all available labs"""
    labs = session.exec(select(Lab).where(Lab.is_active)).all()
    return [
        {
            "id": lab.id,
            "slug": lab.slug,
            "name": lab.name,
            "description": lab.description,
            "ui_url": lab.ui_url,
            "api_url": lab.api_url,
            "session_manager_url": lab.session_manager_url,
            "is_active": lab.is_active,
            "created_at": lab.created_at.isoformat()
        }
        for lab in labs
    ]


@router.post('', response_model=dict)
def create_lab(lab_data: dict, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """Register a new lab (admin only)"""
    # Check if user is admin
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Check if slug already exists
    existing = session.exec(select(Lab).where(Lab.slug == lab_data['slug'])).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Lab with slug '{lab_data['slug']}' already exists")

    # Create the lab
    lab = Lab(
        slug=lab_data['slug'],
        name=lab_data['name'],
        description=lab_data.get('description', ''),
        ui_url=lab_data['ui_url'],
        api_url=lab_data['api_url'],
        session_manager_url=lab_data['session_manager_url'],
        is_active=True
    )

    session.add(lab)
    session.commit()
    session.refresh(lab)

    return {
        "id": lab.id,
        "slug": lab.slug,
        "name": lab.name,
        "description": lab.description,
        "ui_url": lab.ui_url,
        "api_url": lab.api_url,
        "session_manager_url": lab.session_manager_url,
        "is_active": lab.is_active,
        "created_at": lab.created_at.isoformat()
    }


@router.get("/{lab_slug}", response_model=dict)
def get_lab(lab_slug: str, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """Get lab by slug"""
    lab = session.exec(select(Lab).where(Lab.slug == lab_slug)).first()

    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    return {
        "id": lab.id,
        "slug": lab.slug,
        "name": lab.name,
        "description": lab.description,
        "ui_url": lab.ui_url,
        "api_url": lab.api_url,
        "session_manager_url": lab.session_manager_url,
        "is_active": lab.is_active,
        "created_at": lab.created_at.isoformat()
    }


@router.get("/{lab_slug}/access", response_model=dict)
def check_lab_access(lab_slug: str, user_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """
    Check if a user has access to a lab

    A user has access if they're enrolled in a course that has this lab assigned.
    """
    # Get the lab
    lab = session.exec(select(Lab).where(Lab.slug == lab_slug)).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    # Get user's enrollments
    enrollments = session.exec(
        select(Enrollment).where(Enrollment.user_id == user_id)
    ).all()

    if not enrollments:
        return {
            "has_access": False,
            "reason": "User is not enrolled in any courses"
        }

    # Check if any course has this lab assigned
    for enrollment in enrollments:
        assignment = session.exec(
            select(LabAssignment).where(
                LabAssignment.course_id == enrollment.course_id,
                LabAssignment.lab_id == lab.id,
                LabAssignment.is_active
            )
        ).first()

        if assignment:
            return {
                "has_access": True,
                "course_id": enrollment.course_id,
                "assignment_id": assignment.id,
                "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                "points_possible": assignment.points_possible
            }

    return {
        "has_access": False,
        "reason": "Lab is not assigned to any of user's courses"
    }

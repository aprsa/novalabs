from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from datetime import datetime

from ..database import get_session
from ..models import LabAssignment, User, Course, Lab
from ..dependencies import get_current_user

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get('', response_model=List[dict])
def get_assignments(
    course_id: int = None,
    lab_id: int = None,
    is_active: bool = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get lab assignments, optionally filtered by course_id, lab_id, or active status"""
    query = select(LabAssignment)
    
    if course_id is not None:
        query = query.where(LabAssignment.course_id == course_id)
    if lab_id is not None:
        query = query.where(LabAssignment.lab_id == lab_id)
    if is_active is not None:
        query = query.where(LabAssignment.is_active == is_active)
    
    assignments = session.exec(query).all()
    
    result = []
    for assignment in assignments:
        # Fetch related course and lab for display
        course = session.get(Course, assignment.course_id)
        lab = session.get(Lab, assignment.lab_id)
        
        result.append({
            "id": assignment.id,
            "course_id": assignment.course_id,
            "lab_id": assignment.lab_id,
            "title": assignment.title,
            "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
            "points_possible": assignment.points_possible,
            "is_active": assignment.is_active,
            "created_at": assignment.created_at.isoformat(),
            "course": {
                "code": course.code,
                "name": course.name,
                "semester": course.semester
            } if course else None,
            "lab": {
                "slug": lab.slug,
                "name": lab.name
            } if lab else None
        })
    
    return result


@router.post('', response_model=dict)
def create_assignment(
    assignment_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new lab assignment (instructor/admin only)"""
    # Check if user is instructor or admin
    if current_user.role not in ['instructor', 'admin']:
        raise HTTPException(status_code=403, detail="Instructor or admin privileges required")
    
    # Check if course exists
    course = session.get(Course, assignment_data['course_id'])
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if lab exists
    lab = session.get(Lab, assignment_data['lab_id'])
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    
    # Parse due_date if provided
    due_date = None
    if 'due_date' in assignment_data and assignment_data['due_date']:
        if isinstance(assignment_data['due_date'], str):
            due_date = datetime.fromisoformat(assignment_data['due_date'].replace('Z', '+00:00'))
        else:
            due_date = assignment_data['due_date']
    
    # Create assignment
    assignment = LabAssignment(
        course_id=assignment_data['course_id'],
        lab_id=assignment_data['lab_id'],
        title=assignment_data['title'],
        due_date=due_date,
        points_possible=assignment_data.get('points_possible'),
        is_active=assignment_data.get('is_active', True)
    )
    
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    
    return {
        "id": assignment.id,
        "course_id": assignment.course_id,
        "lab_id": assignment.lab_id,
        "title": assignment.title,
        "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
        "points_possible": assignment.points_possible,
        "is_active": assignment.is_active,
        "created_at": assignment.created_at.isoformat(),
        "course": {
            "code": course.code,
            "name": course.name,
            "semester": course.semester
        },
        "lab": {
            "slug": lab.slug,
            "name": lab.name
        }
    }


@router.get('/{assignment_id}', response_model=dict)
def get_assignment(
    assignment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get assignment by ID"""
    assignment = session.get(LabAssignment, assignment_id)
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    course = session.get(Course, assignment.course_id)
    lab = session.get(Lab, assignment.lab_id)
    
    return {
        "id": assignment.id,
        "course_id": assignment.course_id,
        "lab_id": assignment.lab_id,
        "title": assignment.title,
        "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
        "points_possible": assignment.points_possible,
        "is_active": assignment.is_active,
        "created_at": assignment.created_at.isoformat(),
        "course": {
            "code": course.code,
            "name": course.name,
            "semester": course.semester
        } if course else None,
        "lab": {
            "slug": lab.slug,
            "name": lab.name
        } if lab else None
    }


@router.patch('/{assignment_id}', response_model=dict)
def update_assignment(
    assignment_id: int,
    assignment_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update an assignment (instructor/admin only)"""
    # Check if user is instructor or admin
    if current_user.role not in ['instructor', 'admin']:
        raise HTTPException(status_code=403, detail="Instructor or admin privileges required")
    
    assignment = session.get(LabAssignment, assignment_id)
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Update fields if provided
    if 'title' in assignment_data:
        assignment.title = assignment_data['title']
    if 'due_date' in assignment_data:
        if assignment_data['due_date']:
            if isinstance(assignment_data['due_date'], str):
                assignment.due_date = datetime.fromisoformat(assignment_data['due_date'].replace('Z', '+00:00'))
            else:
                assignment.due_date = assignment_data['due_date']
        else:
            assignment.due_date = None
    if 'points_possible' in assignment_data:
        assignment.points_possible = assignment_data['points_possible']
    if 'is_active' in assignment_data:
        assignment.is_active = assignment_data['is_active']
    
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    
    course = session.get(Course, assignment.course_id)
    lab = session.get(Lab, assignment.lab_id)
    
    return {
        "id": assignment.id,
        "course_id": assignment.course_id,
        "lab_id": assignment.lab_id,
        "title": assignment.title,
        "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
        "points_possible": assignment.points_possible,
        "is_active": assignment.is_active,
        "created_at": assignment.created_at.isoformat(),
        "course": {
            "code": course.code,
            "name": course.name,
            "semester": course.semester
        } if course else None,
        "lab": {
            "slug": lab.slug,
            "name": lab.name
        } if lab else None
    }


@router.delete('/{assignment_id}')
def delete_assignment(
    assignment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete an assignment (instructor/admin only)"""
    # Check if user is instructor or admin
    if current_user.role not in ['instructor', 'admin']:
        raise HTTPException(status_code=403, detail="Instructor or admin privileges required")
    
    assignment = session.get(LabAssignment, assignment_id)
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    session.delete(assignment)
    session.commit()
    
    return {"status": "deleted", "id": assignment_id}

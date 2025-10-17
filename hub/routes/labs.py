"""Lab management routes - simplified for sequence progression"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import json

from ..database import get_session
from ..models import Lab, User, UserProgress, ProgressStatus
from ..dependencies import get_current_user

router = APIRouter(prefix="/labs", tags=["labs"])


@router.get('', response_model=list)
def get_labs(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all active labs ordered by sequence"""
    labs = session.exec(
        select(Lab).where(Lab.is_active).order_by(Lab.sequence_order)
    ).all()
    
    return [
        {
            "id": lab.id,
            "ref": lab.ref,
            "name": lab.name,
            "description": lab.description,
            "sequence_order": lab.sequence_order,
            "category": lab.category,
            "prerequisite_refs": json.loads(lab.prerequisite_refs) if lab.prerequisite_refs else [],
            "ui_url": lab.ui_url,
            "max_score": lab.max_score,
            "has_bonus_challenge": lab.has_bonus_challenge,
            "max_bonus_points": lab.max_bonus_points,
            "is_active": lab.is_active,
            "created_at": lab.created_at.isoformat()
        }
        for lab in labs
    ]


@router.post('', response_model=dict)
def create_lab(
    lab_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Register a new lab (admin only)"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    # Check if ref already exists
    existing = session.exec(select(Lab).where(Lab.ref == lab_data['ref'])).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Lab with ref '{lab_data['ref']}' already exists")
    
    # Validate prerequisite refs if provided
    prereq_refs = lab_data.get('prerequisite_refs', [])
    if prereq_refs:
        for prereq_ref in prereq_refs:
            prereq_lab = session.exec(select(Lab).where(Lab.ref == prereq_ref)).first()
            if not prereq_lab:
                raise HTTPException(status_code=400, detail=f"Prerequisite lab '{prereq_ref}' not found")
    
    # Create the lab
    lab = Lab(
        ref=lab_data['ref'],
        name=lab_data['name'],
        description=lab_data.get('description', ''),
        sequence_order=lab_data['sequence_order'],
        category=lab_data.get('category', 'Uncategorized'),
        prerequisite_refs=json.dumps(prereq_refs) if prereq_refs else None,
        ui_url=lab_data['ui_url'],
        max_score=lab_data.get('max_score', 100.0),
        has_bonus_challenge=lab_data.get('has_bonus_challenge', False),
        max_bonus_points=lab_data.get('max_bonus_points', 0.0),
        is_active=True
    )
    
    session.add(lab)
    session.commit()
    session.refresh(lab)
    
    return {
        "id": lab.id,
        "ref": lab.ref,
        "name": lab.name,
        "description": lab.description,
        "sequence_order": lab.sequence_order,
        "category": lab.category,
        "prerequisite_refs": json.loads(lab.prerequisite_refs) if lab.prerequisite_refs else [],
        "ui_url": lab.ui_url,
        "max_score": lab.max_score,
        "has_bonus_challenge": lab.has_bonus_challenge,
        "max_bonus_points": lab.max_bonus_points,
        "is_active": lab.is_active,
        "created_at": lab.created_at.isoformat()
    }


@router.get("/{lab_ref}", response_model=dict)
def get_lab(
    lab_ref: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get lab by ref"""
    lab = session.exec(select(Lab).where(Lab.ref == lab_ref)).first()

    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    return {
        "id": lab.id,
        "ref": lab.ref,
        "name": lab.name,
        "description": lab.description,
        "sequence_order": lab.sequence_order,
        "category": lab.category,
        "prerequisite_refs": json.loads(lab.prerequisite_refs) if lab.prerequisite_refs else [],
        "ui_url": lab.ui_url,
        "max_score": lab.max_score,
        "has_bonus_challenge": lab.has_bonus_challenge,
        "max_bonus_points": lab.max_bonus_points,
        "is_active": lab.is_active,
        "created_at": lab.created_at.isoformat()
    }


@router.get("/{lab_ref}/accessible", response_model=dict)
def check_lab_accessible(lab_ref: str, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """
    Check if user can access this lab (prerequisites met)

    Returns:
    - accessible: bool
    - reason: str (if not accessible)
    - missing_prerequisites: list of lab refs needed
    """
    lab = session.exec(select(Lab).where(Lab.ref == lab_ref)).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    # If no prerequisites, always accessible
    if not lab.prerequisite_refs:
        return {
            'accessible': True,
            'lab_ref': lab_ref,
            'prerequisites_met': True
        }

    try:
        prereq_refs = json.loads(lab.prerequisite_refs)
    except (json.JSONDecodeError, TypeError):
        prereq_refs = []

    if not prereq_refs:
        return {
            'accessible': True,
            'lab_ref': lab_ref,
            'prerequisites_met': True
        }

    # Check each prerequisite
    missing_prereqs = []
    for prereq_ref in prereq_refs:
        prereq_lab = session.exec(select(Lab).where(Lab.ref == prereq_ref)).first()
        if not prereq_lab:
            continue

        # Check user's progress on this prerequisite
        progress = session.exec(
            select(UserProgress).where(
                UserProgress.user_id == current_user.id,
                UserProgress.lab_id == prereq_lab.id
            )
        ).first()

        if not progress or progress.status != ProgressStatus.COMPLETED:
            missing_prereqs.append(prereq_ref)

    if missing_prereqs:
        return {
            'accessible': False,
            'lab_ref': lab_ref,
            'prerequisites_met': False,
            'missing_prerequisites': missing_prereqs,
            'reason': f"Complete {len(missing_prereqs)} prerequisite lab(s) first"
        }

    return {
        'accessible': True,
        'lab_ref': lab_ref,
        'prerequisites_met': True
    }


@router.patch("/{lab_ref}", response_model=dict)
def update_lab(
    lab_ref: str,
    lab_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update lab details (admin only)"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    lab = session.exec(select(Lab).where(Lab.ref == lab_ref)).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    
    # Update allowed fields
    if 'name' in lab_data:
        lab.name = lab_data['name']
    if 'description' in lab_data:
        lab.description = lab_data['description']
    if 'sequence_order' in lab_data:
        lab.sequence_order = lab_data['sequence_order']
    if 'category' in lab_data:
        lab.category = lab_data['category']
    if 'prerequisite_refs' in lab_data:
        lab.prerequisite_refs = json.dumps(lab_data['prerequisite_refs'])
    if 'ui_url' in lab_data:
        lab.ui_url = lab_data['ui_url']
    if 'max_score' in lab_data:
        lab.max_score = lab_data['max_score']
    if 'has_bonus_challenge' in lab_data:
        lab.has_bonus_challenge = lab_data['has_bonus_challenge']
    if 'max_bonus_points' in lab_data:
        lab.max_bonus_points = lab_data['max_bonus_points']
    if 'is_active' in lab_data:
        lab.is_active = lab_data['is_active']
    
    session.add(lab)
    session.commit()
    session.refresh(lab)
    
    return {
        "id": lab.id,
        "ref": lab.ref,
        "name": lab.name,
        "description": lab.description,
        "sequence_order": lab.sequence_order,
        "category": lab.category,
        "prerequisite_refs": json.loads(lab.prerequisite_refs) if lab.prerequisite_refs else [],
        "ui_url": lab.ui_url,
        "max_score": lab.max_score,
        "has_bonus_challenge": lab.has_bonus_challenge,
        "max_bonus_points": lab.max_bonus_points,
        "is_active": lab.is_active,
        "created_at": lab.created_at.isoformat()
    }


@router.delete("/{lab_ref}")
def delete_lab(
    lab_ref: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete a lab (admin only)"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    lab = session.exec(select(Lab).where(Lab.ref == lab_ref)).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    
    session.delete(lab)
    session.commit()
    
    return {"status": "deleted", "ref": lab_ref}

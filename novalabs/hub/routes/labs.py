"""Lab management routes - simplified for sequence progression."""

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_current_user
from ..models import ProgressStatus, User, CourseProgress
from novalabs.core.models import Lab
from novalabs.common.config import NovaLabsConfig

router = APIRouter(prefix="/labs", tags=["labs"])

# Load config
config = NovaLabsConfig()


def serialize_lab(lab: Lab) -> dict:
    prereqs = lab.prerequisite_refs or []
    if isinstance(prereqs, str):
        try:
            prereqs = json.loads(prereqs)
        except (json.JSONDecodeError, TypeError):
            prereqs = []

    return {
        "id": lab.id,
        "ref": lab.slug,
        "name": lab.title,
        "description": lab.description,
        "sequence_order": lab.sort_order,
        "category": lab.category,
        "prerequisite_refs": prereqs,
        "ui_url": lab.ui_url,
        "max_score": lab.pre_quiz_max_points + lab.post_quiz_max_points,
        "has_bonus_challenge": lab.has_bonus_challenge,
        "max_bonus_points": lab.max_bonus_points,
        "is_active": lab.is_active,
        "created_at": lab.created_at.isoformat() if lab.created_at else None,
    }


async def require_admin(user: User) -> None:
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin privileges required")


@router.get('', response_model=list)
async def get_labs(current_user: User = Depends(get_current_user)):
    """Get all active labs ordered by sequence."""
    labs = await Lab.filter(is_active=True).order_by('sort_order').all()
    return [serialize_lab(lab) for lab in labs]


@router.post('', response_model=dict)
async def create_lab(lab_data: dict, current_user: User = Depends(get_current_user)):
    """Register a new lab (admin only)."""
    await require_admin(current_user)

    existing = await Lab.get_or_none(slug=lab_data['ref'])
    if existing:
        raise HTTPException(status_code=400, detail=f"Lab with ref '{lab_data['ref']}' already exists")

    prereq_refs: List[str] = lab_data.get('prerequisite_refs', [])
    if prereq_refs:
        for prereq_ref in prereq_refs:
            prereq_lab = await Lab.get_or_none(slug=prereq_ref)
            if not prereq_lab:
                raise HTTPException(status_code=400, detail=f"Prerequisite lab '{prereq_ref}' not found")

    lab = Lab(
        slug=lab_data['ref'],
        title=lab_data['name'],
        description=lab_data.get('description', ''),
        sort_order=lab_data['sequence_order'],
        category=lab_data.get('category', 'Uncategorized'),
        prerequisite_refs=prereq_refs or [],
        ui_url=lab_data['ui_url'],
        api_url=lab_data.get('api_url'),
        session_manager_url=lab_data.get('session_manager_url'),
        pre_quiz_max_points=lab_data.get('max_score', 100.0) / 2,
        post_quiz_max_points=lab_data.get('max_score', 100.0) / 2,
        has_bonus_challenge=lab_data.get('has_bonus_challenge', False),
        max_bonus_points=lab_data.get('max_bonus_points', 0.0),
        is_active=True,
    )

    await lab.save()
    return serialize_lab(lab)


@router.get("/{lab_ref}", response_model=dict)
async def get_lab(lab_ref: str, current_user: User = Depends(get_current_user)):
    """Get lab by ref."""
    lab = await Lab.get_or_none(slug=lab_ref)

    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    return serialize_lab(lab)


@router.get("/{lab_ref}/accessible", response_model=dict)
async def check_lab_accessible(lab_ref: str, current_user: User = Depends(get_current_user)):
    """Check if user can access this lab (prerequisites met)."""
    lab = await Lab.get_or_none(slug=lab_ref)
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    if config.data.get('settings', {}).get('disable_lab_dependency_checks', False):
        return {
            'accessible': True,
            'lab_ref': lab_ref,
            'prerequisites_met': True,
            'note': 'Dependency checks disabled',
        }

    prereq_refs = lab.prerequisite_refs or []
    if isinstance(prereq_refs, str):
        try:
            prereq_refs = json.loads(prereq_refs)
        except (json.JSONDecodeError, TypeError):
            prereq_refs = []

    if not prereq_refs:
        return {
            'accessible': True,
            'lab_ref': lab_ref,
            'prerequisites_met': True,
        }

    missing_prereqs = []
    for prereq_ref in prereq_refs:
        prereq_lab = await Lab.get_or_none(slug=prereq_ref)
        if not prereq_lab:
            continue

        progress = await CourseProgress.get_or_none(user_id=current_user.id, lab_id=prereq_lab.id)
        if not progress or progress.status != ProgressStatus.COMPLETED.value:
            missing_prereqs.append(prereq_ref)

    if missing_prereqs:
        return {
            'accessible': False,
            'lab_ref': lab_ref,
            'prerequisites_met': False,
            'missing_prerequisites': missing_prereqs,
            'reason': f"Complete {len(missing_prereqs)} prerequisite lab(s) first",
        }

    return {
        'accessible': True,
        'lab_ref': lab_ref,
        'prerequisites_met': True,
    }


@router.patch("/{lab_ref}", response_model=dict)
async def update_lab(lab_ref: str, lab_data: dict, current_user: User = Depends(get_current_user)):
    """Update lab details (admin only)."""
    await require_admin(current_user)

    lab = await Lab.get_or_none(slug=lab_ref)
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    if 'name' in lab_data:
        lab.title = lab_data['name']
    if 'description' in lab_data:
        lab.description = lab_data['description']
    if 'sequence_order' in lab_data:
        lab.sort_order = lab_data['sequence_order']
    if 'category' in lab_data:
        lab.category = lab_data['category']
    if 'prerequisite_refs' in lab_data:
        lab.prerequisite_refs = lab_data['prerequisite_refs']
    if 'ui_url' in lab_data:
        lab.ui_url = lab_data['ui_url']
    if 'api_url' in lab_data:
        lab.api_url = lab_data['api_url']
    if 'session_manager_url' in lab_data:
        lab.session_manager_url = lab_data['session_manager_url']
    if 'max_score' in lab_data:
        total_score = lab_data['max_score']
        lab.pre_quiz_max_points = total_score / 2
        lab.post_quiz_max_points = total_score / 2
    if 'has_bonus_challenge' in lab_data:
        lab.has_bonus_challenge = lab_data['has_bonus_challenge']
    if 'max_bonus_points' in lab_data:
        lab.max_bonus_points = lab_data['max_bonus_points']
    if 'is_active' in lab_data:
        lab.is_active = lab_data['is_active']

    await lab.save()
    await lab.refresh_from_db()

    return serialize_lab(lab)


@router.delete("/{lab_ref}")
async def delete_lab(lab_ref: str, current_user: User = Depends(get_current_user)):
    """Delete a lab (admin only)."""
    await require_admin(current_user)

    lab = await Lab.get_or_none(slug=lab_ref)
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    await lab.delete()

    return {"status": "deleted", "ref": lab_ref}

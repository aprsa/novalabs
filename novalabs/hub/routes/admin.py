"""Admin routes for managing user progress and overrides."""

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_current_user
from ..models import ProgressStatus, User, CourseProgress
from novalabs.core.models import Lab
from .progress import update_user_rank_and_score

router = APIRouter(prefix="/admin", tags=["admin"])


def ensure_admin_or_instructor(user: User) -> None:
    if user.role not in ['admin', 'instructor']:
        raise HTTPException(status_code=403, detail="Admin or instructor privileges required")


@router.get('/users/{user_id}/progress', response_model=dict)
async def get_user_progress(user_id: int, current_user: User = Depends(get_current_user)):
    """Get any user's progress (admin/instructor only)."""
    ensure_admin_or_instructor(current_user)

    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    labs = await Lab.filter(is_active=True).order_by('sort_order').all()
    progress_records = await CourseProgress.filter(user_id=user_id).all()
    progress_map = {p.lab_id: p for p in progress_records}

    labs_with_progress = []
    for lab in labs:
        progress = progress_map.get(lab.id)

        labs_with_progress.append({
            "lab": {
                "id": lab.id,
                "ref": lab.slug,
                "name": lab.title,
                "sequence_order": lab.sort_order,
                "category": lab.category,
            },
            "progress": {
                "status": progress.status if progress else ProgressStatus.LOCKED.value,
                "score": progress.score if progress else None,
                "bonus_points": progress.bonus_points if progress else 0.0,
                "attempts": progress.attempts if progress else 0,
                "started_at": progress.started_at.isoformat() if progress and progress.started_at else None,
                "completed_at": progress.completed_at.isoformat() if progress and progress.completed_at else None,
                "instructor_notes": progress.instructor_notes if progress else None,
                "score_overridden": progress.score_overridden if progress else False,
            },
        })

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "rank": user.rank,
            "total_score": user.total_score,
            "total_bonus_points": user.total_bonus_points,
        },
        "labs": labs_with_progress,
    }


@router.patch('/users/{user_id}/labs/{lab_ref}', response_model=dict)
async def override_lab_score(
    user_id: int,
    lab_ref: str,
    override_data: dict,
    current_user: User = Depends(get_current_user),
):
    """Override a user's lab score (admin/instructor only)."""
    ensure_admin_or_instructor(current_user)

    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    lab = await Lab.get_or_none(slug=lab_ref)
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    progress = await CourseProgress.get_or_none(user_id=user_id, lab_id=lab.id)
    if not progress:
        raise HTTPException(status_code=404, detail="No progress record found for this lab")

    if 'score' in override_data:
        progress.score = override_data['score']
        progress.score_overridden = True

    if 'bonus_points' in override_data:
        progress.bonus_points = override_data['bonus_points']

    if 'instructor_notes' in override_data:
        progress.instructor_notes = override_data['instructor_notes']

    await progress.save()

    await update_user_rank_and_score(user)

    return {
        'status': 'updated',
        'user_id': user_id,
        'lab_ref': lab_ref,
        'score': progress.score,
        'bonus_points': progress.bonus_points,
        'instructor_notes': progress.instructor_notes,
    }

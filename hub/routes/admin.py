"""Admin routes for managing user progress and overrides"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import User, Lab, UserProgress, ProgressStatus
from ..dependencies import get_current_user
from .progress import update_user_rank_and_score

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get('/users/{user_id}/progress', response_model=dict)
def get_user_progress(user_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """Get any user's progress (admin/instructor only)"""
    if current_user.role not in ['admin', 'instructor']:
        raise HTTPException(status_code=403, detail="Admin or instructor privileges required")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all labs
    labs = session.exec(
        select(Lab).where(Lab.is_active).order_by(Lab.sequence_order)
    ).all()

    # Get user's progress
    progress_records = session.exec(
        select(UserProgress).where(UserProgress.user_id == user_id)
    ).all()

    progress_map = {p.lab_id: p for p in progress_records}

    labs_with_progress = []
    for lab in labs:
        progress = progress_map.get(lab.id)

        labs_with_progress.append({
            "lab": {
                "id": lab.id,
                "ref": lab.ref,
                "name": lab.name,
                "sequence_order": lab.sequence_order,
                "category": lab.category
            },
            "progress": {
                "status": progress.status if progress else ProgressStatus.LOCKED,
                "score": progress.score if progress else None,
                "bonus_points": progress.bonus_points if progress else 0.0,
                "attempts": progress.attempts if progress else 0,
                "started_at": progress.started_at.isoformat() if progress and progress.started_at else None,
                "completed_at": progress.completed_at.isoformat() if progress and progress.completed_at else None,
                "instructor_notes": progress.instructor_notes if progress else None,
                "score_overridden": progress.score_overridden if progress else False
            }
        })

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "rank": user.rank,
            "total_score": user.total_score,
            "total_bonus_points": user.total_bonus_points
        },
        "labs": labs_with_progress
    }


@router.patch('/users/{user_id}/labs/{lab_ref}', response_model=dict)
def override_lab_score(
    user_id: int,
    lab_ref: str,
    override_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Override a user's lab score (admin/instructor only)

    Expected data:
    {
        "score": 95.0,
        "bonus_points": 5.0,
        "instructor_notes": "Excellent work on bonus challenge"
    }
    """
    if current_user.role not in ['admin', 'instructor']:
        raise HTTPException(status_code=403, detail="Admin or instructor privileges required")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    lab = session.exec(select(Lab).where(Lab.ref == lab_ref)).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    progress = session.exec(
        select(UserProgress).where(
            UserProgress.user_id == user_id,
            UserProgress.lab_id == lab.id
        )
    ).first()

    if not progress:
        raise HTTPException(status_code=404, detail="No progress record found for this lab")

    # Update score and notes
    if 'score' in override_data:
        progress.score = override_data['score']
        progress.score_overridden = True

    if 'bonus_points' in override_data:
        progress.bonus_points = override_data['bonus_points']

    if 'instructor_notes' in override_data:
        progress.instructor_notes = override_data['instructor_notes']

    session.add(progress)
    session.commit()

    # Recalculate user totals
    update_user_rank_and_score(user, session)

    return {
        'status': 'updated',
        'user_id': user_id,
        'lab_ref': lab_ref,
        'score': progress.score,
        'bonus_points': progress.bonus_points,
        'instructor_notes': progress.instructor_notes
    }

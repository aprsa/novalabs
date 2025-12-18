"""Progress tracking routes for lab sequence."""

from datetime import datetime, UTC
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_current_user
from ..models import ProgressStatus, User, CourseProgress, UserRank
from novalabs.core.models import Lab
from novalabs.common.config import NovaLabsConfig

router = APIRouter(prefix="/progress", tags=["progress"])

# Load config
config = NovaLabsConfig()


def calculate_rank(total_labs: int, completed_labs: int) -> str:
    """Calculate user rank based on completion percentage."""
    if total_labs == 0:
        return UserRank.DABBLER.value

    ranks: List[UserRank] = list(UserRank)
    idx = int(round(completed_labs / total_labs * (len(ranks) - 1)))
    return ranks[idx].value


async def prerequisites_met(user_id: int, lab: Lab) -> bool:
    """Check if user has completed all prerequisite labs."""
    if config.data.get('settings', {}).get('disable_lab_dependency_checks', False):
        return True

    prereq_refs = lab.prerequisite_refs or []
    if isinstance(prereq_refs, str):
        try:
            prereq_refs = json.loads(prereq_refs)
        except (json.JSONDecodeError, TypeError):
            prereq_refs = []

    if not prereq_refs:
        return True

    prereq_labs = await Lab.filter(slug__in=prereq_refs).all()
    if not prereq_labs:
        return True

    for prereq_lab in prereq_labs:
        progress = await CourseProgress.get_or_none(user_id=user_id, lab_id=prereq_lab.id)
        if not progress or progress.status != ProgressStatus.COMPLETED.value:
            return False

    return True


async def update_user_rank_and_score(user: User) -> None:
    """Recalculate and update user's rank and totals."""
    labs = await Lab.filter(is_active=True).all()
    user_progress_list = await CourseProgress.filter(user_id=user.id).all()

    completed_count = sum(1 for p in user_progress_list if p.status == ProgressStatus.COMPLETED.value)
    total_score = sum(p.score or 0 for p in user_progress_list if p.score is not None)
    total_bonus = sum(p.bonus_points or 0 for p in user_progress_list)

    user.rank = calculate_rank(len(labs), completed_count)
    user.total_score = total_score
    user.total_bonus_points = total_bonus

    await user.save()


def serialize_lab_meta(lab: Lab) -> dict:
    max_score = (lab.pre_quiz_max_points or 0) + (lab.post_quiz_max_points or 0)
    return {
        'id': lab.id,
        'ref': lab.slug,
        'name': lab.title,
        'description': lab.description,
        'sequence_order': lab.sort_order,
        'category': lab.category,
        'max_score': max_score,
        'has_bonus_challenge': lab.has_bonus_challenge,
        'max_bonus_points': lab.max_bonus_points,
        'ui_url': lab.ui_url,
    }


@router.get('', response_model=dict)
async def get_my_progress(current_user: User = Depends(get_current_user)):
    """Get current user's progress across all labs."""
    labs = await Lab.filter(is_active=True).order_by('sort_order').all()
    progress_records = await CourseProgress.filter(user_id=current_user.id).all()

    progress_map = {p.lab_id: p for p in progress_records}

    labs_with_progress = []
    for lab in labs:
        progress = progress_map.get(lab.id)

        if not progress:
            can_access = await prerequisites_met(current_user.id, lab)
            status = ProgressStatus.UNLOCKED.value if can_access else ProgressStatus.LOCKED.value

            labs_with_progress.append({
                'meta': serialize_lab_meta(lab),
                'progress': {
                    'status': status,
                    'score': None,
                    'bonus_points': 0.0,
                    'attempts': 0,
                    'started_at': None,
                    'completed_at': None,
                },
            })
        else:
            labs_with_progress.append({
                'meta': serialize_lab_meta(lab),
                'progress': {
                    'status': progress.status,
                    'score': progress.score,
                    'bonus_points': progress.bonus_points,
                    'attempts': progress.attempts,
                    'started_at': progress.started_at.isoformat() if progress.started_at else None,
                    'completed_at': progress.completed_at.isoformat() if progress.completed_at else None,
                },
            })

    return {
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'first_name': current_user.first_name,
            'last_name': current_user.last_name,
            'rank': current_user.rank,
            'total_score': current_user.total_score,
            'total_bonus_points': current_user.total_bonus_points,
        },
        'labs': labs_with_progress,
    }


@router.get('/lab/{lab_ref}', response_model=dict)
async def get_lab_progress(lab_ref: str, current_user: User = Depends(get_current_user)):
    """Get user's progress for a specific lab."""
    lab = await Lab.get_or_none(slug=lab_ref)
    if not lab:
        raise HTTPException(status_code=404, detail='Lab not found')

    progress = await CourseProgress.get_or_none(user_id=current_user.id, lab_id=lab.id)

    if not progress:
        can_access = await prerequisites_met(current_user.id, lab)
        status = ProgressStatus.UNLOCKED.value if can_access else ProgressStatus.LOCKED.value

        return {
            'meta': {
                'ref': lab.slug,
                'name': lab.title,
                'sequence_order': lab.sort_order,
                'category': lab.category,
            },
            'progress': {
                'status': status,
                'score': None,
                'bonus_points': 0.0,
                'attempts': 0,
            },
        }

    return {
        'meta': {
            'ref': lab.slug,
            'name': lab.title,
            'sequence_order': lab.sort_order,
            'category': lab.category,
        },
        'progress': {
            'status': progress.status,
            'score': progress.score,
            'bonus_points': progress.bonus_points,
            'attempts': progress.attempts,
            'started_at': progress.started_at.isoformat() if progress.started_at else None,
            'completed_at': progress.completed_at.isoformat() if progress.completed_at else None,
        },
    }


@router.post('/lab/{lab_ref}/start', response_model=dict)
async def start_lab(lab_ref: str, current_user: User = Depends(get_current_user)):
    """Start a lab (marks as in_progress, increments attempts)."""
    lab = await Lab.get_or_none(slug=lab_ref)
    if not lab:
        raise HTTPException(status_code=404, detail='Lab not found')

    if not await prerequisites_met(current_user.id, lab):
        raise HTTPException(status_code=403, detail='Prerequisites not met')

    progress = await CourseProgress.get_or_none(user_id=current_user.id, lab_id=lab.id)

    if not progress:
        progress = CourseProgress(
            user_id=current_user.id,
            lab_id=lab.id,
            status=ProgressStatus.IN_PROGRESS.value,
            score=0.0,
            bonus_points=0.0,
            attempts=1,
            started_at=datetime.now(UTC),
            last_activity=datetime.now(UTC),
        )
    else:
        now = datetime.now(UTC)
        if progress.status == ProgressStatus.COMPLETED.value:
            progress.attempts += 1
            progress.status = ProgressStatus.IN_PROGRESS.value
            progress.last_activity = now
        elif progress.status == ProgressStatus.IN_PROGRESS.value:
            progress.last_activity = now
        else:
            progress.attempts += 1
            progress.status = ProgressStatus.IN_PROGRESS.value
            progress.last_activity = now

        if not progress.started_at:
            progress.started_at = now

    await progress.save()

    return {
        'status': progress.status,
        'lab_ref': lab_ref,
        'attempts': progress.attempts,
        'score': progress.score,
        'bonus_points': progress.bonus_points,
        'started_at': progress.started_at.isoformat() if progress.started_at else None,
    }


@router.post('/lab/{lab_ref}/complete', response_model=dict)
async def complete_lab(lab_ref: str, completion_data: dict, current_user: User = Depends(get_current_user)):
    """Mark lab as completed with score."""
    lab = await Lab.get_or_none(slug=lab_ref)
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    progress = await CourseProgress.get_or_none(user_id=current_user.id, lab_id=lab.id)
    if not progress:
        raise HTTPException(status_code=400, detail="Lab not started")

    if progress.status not in [ProgressStatus.IN_PROGRESS.value, ProgressStatus.COMPLETED.value]:
        raise HTTPException(status_code=400, detail="Lab must be started before completion")

    score = completion_data.get('score')
    if score is None:
        raise HTTPException(status_code=400, detail="Score required")

    max_score = (lab.pre_quiz_max_points or 0) + (lab.post_quiz_max_points or 0)
    if not (0 <= score <= max_score):
        raise HTTPException(status_code=400, detail=f"Score must be between 0 and {max_score}")

    bonus_points = completion_data.get('bonus_points', 0.0)
    if bonus_points < 0 or bonus_points > lab.max_bonus_points:
        raise HTTPException(status_code=400, detail=f"Bonus points must be between 0 and {lab.max_bonus_points}")

    now = datetime.now(UTC)
    progress.status = ProgressStatus.COMPLETED.value
    progress.score = score
    progress.bonus_points = bonus_points
    progress.completed_at = now
    progress.last_activity = now

    await progress.save()

    await update_user_rank_and_score(current_user)
    await current_user.refresh_from_db()

    return {
        'status': 'completed',
        'lab_ref': lab_ref,
        'score': progress.score,
        'bonus_points': progress.bonus_points,
        'completed_at': progress.completed_at.isoformat() if progress.completed_at else None,
        'user_rank': current_user.rank,
        'user_total_score': current_user.total_score,
    }

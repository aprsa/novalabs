"""Progress tracking routes for lab sequence"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime, UTC
import json

from ..database import get_session
from ..models import User, Lab, UserProgress, ProgressStatus, UserRank
from ..dependencies import get_current_user

router = APIRouter(prefix="/progress", tags=["progress"])


def calculate_rank(total_labs: int, completed_labs: int) -> str:
    """Calculate user rank based on completion percentage"""
    ranks = list(UserRank)
    idx = int(round(completed_labs / total_labs * (len(ranks) - 1)))
    return ranks[idx]


def prerequisites_met(user_id: int, lab: Lab, session: Session) -> bool:
    """Check if user has completed all prerequisite labs"""
    if not lab.prerequisite_refs:
        return True  # No prerequisites

    try:
        prereq_refs = json.loads(lab.prerequisite_refs)
    except (json.JSONDecodeError, TypeError):
        return True  # Invalid JSON, assume no prereqs

    if not prereq_refs:
        return True

    # Get all prerequisite labs
    prereq_labs = session.exec(
        select(Lab).where(Lab.ref.in_(prereq_refs))
    ).all()

    # Check if user has completed each prerequisite
    for prereq_lab in prereq_labs:
        progress = session.exec(
            select(UserProgress).where(
                UserProgress.user_id == user_id,
                UserProgress.lab_id == prereq_lab.id
            )
        ).first()

        if not progress or progress.status != ProgressStatus.COMPLETED:
            return False

    return True


def update_user_rank_and_score(user: User, session: Session):
    """Recalculate and update user's rank and total scores"""
    # Get all labs
    total_labs = session.exec(
        select(Lab).where(Lab.is_active)
    ).all()

    # Get user's progress
    user_progress_list = session.exec(
        select(UserProgress).where(UserProgress.user_id == user.id)
    ).all()

    # Calculate totals
    completed_count = sum(1 for p in user_progress_list if p.status == ProgressStatus.COMPLETED)
    total_score = sum(p.score or 0 for p in user_progress_list if p.score is not None)
    total_bonus = sum(p.bonus_points for p in user_progress_list)

    # Update user
    user.rank = calculate_rank(len(total_labs), completed_count)
    user.total_score = total_score
    user.total_bonus_points = total_bonus

    session.add(user)
    session.commit()


@router.get('', response_model=dict)
def get_my_progress(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """
    Get current user's progress across all labs

    Returns:
    - User rank and stats
    - All labs with user's progress status
    - Which labs are accessible (unlocked/in_progress)
    """
    # Get all labs ordered by sequence
    labs = session.exec(
        select(Lab).where(Lab.is_active).order_by(Lab.sequence_order)
    ).all()

    # Get user's progress for all labs
    progress_records = session.exec(
        select(UserProgress).where(UserProgress.user_id == current_user.id)
    ).all()

    # Create progress lookup
    progress_map = {p.lab_id: p for p in progress_records}

    # Build response
    labs_with_progress = []
    for lab in labs:
        progress = progress_map.get(lab.id)

        # Determine status if no progress record exists
        if not progress:
            # Check if prerequisites are met
            can_access = prerequisites_met(current_user.id, lab, session)
            status = ProgressStatus.UNLOCKED if can_access else ProgressStatus.LOCKED

            labs_with_progress.append({
                "lab": {
                    "id": lab.id,
                    "ref": lab.ref,
                    "name": lab.name,
                    "description": lab.description,
                    "sequence_order": lab.sequence_order,
                    "category": lab.category,
                    "max_score": lab.max_score,
                    "has_bonus_challenge": lab.has_bonus_challenge,
                    "max_bonus_points": lab.max_bonus_points,
                    "ui_url": lab.ui_url
                },
                "progress": {
                    "status": status,
                    "score": None,
                    "bonus_points": 0.0,
                    "attempts": 0,
                    "started_at": None,
                    "completed_at": None
                }
            })
        else:
            labs_with_progress.append({
                "lab": {
                    "id": lab.id,
                    "ref": lab.ref,
                    "name": lab.name,
                    "description": lab.description,
                    "sequence_order": lab.sequence_order,
                    "category": lab.category,
                    "max_score": lab.max_score,
                    "has_bonus_challenge": lab.has_bonus_challenge,
                    "max_bonus_points": lab.max_bonus_points,
                    "ui_url": lab.ui_url
                },
                "progress": {
                    "status": progress.status,
                    "score": progress.score,
                    "bonus_points": progress.bonus_points,
                    "attempts": progress.attempts,
                    "started_at": progress.started_at.isoformat() if progress.started_at else None,
                    "completed_at": progress.completed_at.isoformat() if progress.completed_at else None
                }
            })

    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "rank": current_user.rank,
            "total_score": current_user.total_score,
            "total_bonus_points": current_user.total_bonus_points
        },
        "labs": labs_with_progress
    }


@router.get('/lab/{lab_ref}', response_model=dict)
def get_lab_progress(lab_ref: str, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """Get user's progress for a specific lab"""
    lab = session.exec(select(Lab).where(Lab.ref == lab_ref)).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    progress = session.exec(
        select(UserProgress).where(
            UserProgress.user_id == current_user.id,
            UserProgress.lab_id == lab.id
        )
    ).first()

    if not progress:
        # Check if accessible
        can_access = prerequisites_met(current_user.id, lab, session)
        status = ProgressStatus.UNLOCKED if can_access else ProgressStatus.LOCKED

        return {
            "lab": {
                "ref": lab.ref,
                "name": lab.name,
                "sequence_order": lab.sequence_order,
                "category": lab.category
            },
            "progress": {
                "status": status,
                "score": None,
                "bonus_points": 0.0,
                "attempts": 0
            }
        }

    return {
        "lab": {
            "ref": lab.ref,
            "name": lab.name,
            "sequence_order": lab.sequence_order,
            "category": lab.category
        },
        "progress": {
            "status": progress.status,
            "score": progress.score,
            "bonus_points": progress.bonus_points,
            "attempts": progress.attempts,
            "started_at": progress.started_at.isoformat() if progress.started_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None
        }
    }


@router.post('/lab/{lab_ref}/start', response_model=dict)
def start_lab(lab_ref: str, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """Start a lab (marks as in_progress, increments attempts)"""
    lab = session.exec(select(Lab).where(Lab.ref == lab_ref)).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    # Check prerequisites
    if not prerequisites_met(current_user.id, lab, session):
        raise HTTPException(status_code=403, detail="Prerequisites not met")

    # Get or create progress record
    progress = session.exec(
        select(UserProgress).where(
            UserProgress.user_id == current_user.id,
            UserProgress.lab_id == lab.id
        )
    ).first()

    if not progress:
        progress = UserProgress(
            user_id=current_user.id,
            lab_id=lab.id,
            status=ProgressStatus.IN_PROGRESS,
            score=0.0,
            bonus_points=0.0,
            attempts=1,
            started_at=datetime.now(UTC),
            last_activity=datetime.now(UTC)
        )
    else:
        # Update existing progress
        # Allow retaking completed labs
        if progress.status == ProgressStatus.COMPLETED:
            # Retake: increment attempts and set to in_progress
            progress.attempts += 1
            progress.status = ProgressStatus.IN_PROGRESS
            progress.last_activity = datetime.now(UTC)
            # Keep previous score/bonus - will be overwritten on next completion
        elif progress.status == ProgressStatus.IN_PROGRESS:
            # Already in progress - just update activity time, don't increment attempts
            progress.last_activity = datetime.now(UTC)
        else:
            # Was UNLOCKED/LOCKED - new attempt
            progress.attempts += 1
            progress.status = ProgressStatus.IN_PROGRESS
            progress.last_activity = datetime.now(UTC)

        if not progress.started_at:
            progress.started_at = datetime.now(UTC)

    session.add(progress)
    session.commit()
    session.refresh(progress)

    return {
        'status': progress.status,
        'lab_ref': lab_ref,
        'attempts': progress.attempts,
        'score': progress.score,
        'bonus_points': progress.bonus_points,
        'started_at': progress.started_at.isoformat()
    }


@router.post('/lab/{lab_ref}/complete', response_model=dict)
def complete_lab(lab_ref: str, completion_data: dict, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """
    Mark lab as completed with score

    Expected data:
    {
        "score": 85.5,  # 0-100
        "bonus_points": 10.0  # Optional
    }
    """
    lab = session.exec(select(Lab).where(Lab.ref == lab_ref)).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    # Get progress record
    progress = session.exec(
        select(UserProgress).where(
            UserProgress.user_id == current_user.id,
            UserProgress.lab_id == lab.id
        )
    ).first()

    if not progress:
        raise HTTPException(status_code=400, detail="Lab not started")

    # Allow completion if in progress (including retakes)
    if progress.status not in [ProgressStatus.IN_PROGRESS, ProgressStatus.COMPLETED]:
        raise HTTPException(status_code=400, detail="Lab must be started before completion")

    # Validate score
    score = completion_data.get('score')
    if score is None:
        raise HTTPException(status_code=400, detail="Score required")

    if not (0 <= score <= lab.max_score):
        raise HTTPException(status_code=400, detail=f"Score must be between 0 and {lab.max_score}")

    # Validate bonus points
    bonus_points = completion_data.get('bonus_points', 0.0)
    if bonus_points < 0 or bonus_points > lab.max_bonus_points:
        raise HTTPException(status_code=400, detail=f"Bonus points must be between 0 and {lab.max_bonus_points}")

    # Update progress
    progress.status = ProgressStatus.COMPLETED
    progress.score = score
    progress.bonus_points = completion_data.get('bonus_points', 0.0)
    progress.completed_at = datetime.now(UTC)
    progress.last_activity = datetime.now(UTC)

    session.add(progress)
    session.commit()

    # Update user rank and totals
    update_user_rank_and_score(current_user, session)
    session.refresh(current_user)

    return {
        "status": "completed",
        "lab_ref": lab_ref,
        "score": progress.score,
        "bonus_points": progress.bonus_points,
        "completed_at": progress.completed_at.isoformat(),
        "user_rank": current_user.rank,
        "user_total_score": current_user.total_score
    }

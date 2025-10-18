from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime, timedelta, UTC
import secrets
import json

from ..database import get_session
from ..models import UserSession, User
from ..dependencies import get_current_user

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post('/create')
async def create_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Create a new server-side session"""
    # Generate unique session ID
    session_id = secrets.token_urlsafe(32)

    # Get token from request (it's already validated by get_current_user)
    # In production, you'd extract this from the request header

    # Create session with 7-day expiration
    user_session = UserSession(
        session_id=session_id,
        user_id=current_user.id,
        token="",  # Will be set by client
        state="{}",  # Empty JSON object
        expires_at=datetime.now(UTC) + timedelta(days=7)
    )

    db.add(user_session)
    db.commit()
    db.refresh(user_session)

    return {
        'session_id': session_id,
        'expires_at': user_session.expires_at.isoformat()
    }


@router.get('/{session_id}')
async def get_session_data(
    session_id: str,
    db: Session = Depends(get_session)
):
    """Get session by ID"""
    user_session = db.exec(
        select(UserSession).where(
            UserSession.session_id == session_id,
            UserSession.is_active,
            UserSession.expires_at > datetime.now(UTC)
        )
    ).first()

    if not user_session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    # Update last activity
    user_session.last_activity = datetime.now(UTC)
    db.add(user_session)
    db.commit()

    return {
        'session_id': user_session.session_id,
        'user_id': user_session.user_id,
        'token': user_session.token,
        'state': json.loads(user_session.state) if user_session.state else {},
        'last_activity': user_session.last_activity.isoformat()
    }


@router.patch('/{session_id}')
async def update_session(
    session_id: str,
    update_data: dict,
    db: Session = Depends(get_session)
):
    """Update session state or token"""
    user_session = db.exec(
        select(UserSession).where(
            UserSession.session_id == session_id,
            UserSession.is_active
        )
    ).first()

    if not user_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update token if provided
    if 'token' in update_data:
        user_session.token = update_data['token']

    # Update state if provided
    if 'state' in update_data:
        user_session.state = json.dumps(update_data['state'])

    user_session.last_activity = datetime.now(UTC)

    db.add(user_session)
    db.commit()

    return {'status': 'updated'}


@router.delete('/{session_id}')
async def delete_session(
    session_id: str,
    db: Session = Depends(get_session)
):
    """End a session (logout)"""
    user_session = db.exec(
        select(UserSession).where(UserSession.session_id == session_id)
    ).first()

    if user_session:
        user_session.is_active = False
        db.add(user_session)
        db.commit()

    return {'status': 'deleted'}


@router.get('/user/{user_id}')
async def get_user_sessions(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get all active sessions for a user"""
    # Only allow users to see their own sessions (or admins to see any)
    if current_user.id != user_id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")

    sessions = db.exec(
        select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_active,
            UserSession.expires_at > datetime.now(UTC)
        ).order_by(UserSession.last_activity.desc())
    ).all()

    return [
        {
            'session_id': s.session_id,
            'created_at': s.created_at.isoformat(),
            'last_activity': s.last_activity.isoformat(),
            'expires_at': s.expires_at.isoformat()
        }
        for s in sessions
    ]

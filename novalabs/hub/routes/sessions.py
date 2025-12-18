from datetime import datetime, timedelta, UTC
import json
import secrets

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_current_user
from ..models import User, UserSession

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post('/create')
async def create_session(current_user: User = Depends(get_current_user)):
    """Create a new server-side session."""
    session_id = secrets.token_urlsafe(32)

    user_session = await UserSession.create(
        session_id=session_id,
        user_id=current_user.id,
        token="",
        state="{}",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    return {
        'session_id': session_id,
        'expires_at': user_session.expires_at.isoformat(),
    }


@router.get('/{session_id}')
async def get_session_data(session_id: str):
    """Get session by ID."""
    user_session = await UserSession.filter(
        session_id=session_id,
        is_active=True,
        expires_at__gt=datetime.now(UTC),
    ).first()

    if not user_session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    user_session.last_activity = datetime.now(UTC)
    await user_session.save()

    return {
        'session_id': user_session.session_id,
        'user_id': user_session.user_id,
        'token': user_session.token,
        'state': json.loads(user_session.state) if user_session.state else {},
        'last_activity': user_session.last_activity.isoformat(),
    }


@router.patch('/{session_id}')
async def update_session(session_id: str, update_data: dict):
    """Update session state or token."""
    user_session = await UserSession.filter(session_id=session_id, is_active=True).first()

    if not user_session:
        raise HTTPException(status_code=404, detail="Session not found")

    if 'token' in update_data:
        user_session.token = update_data['token']

    if 'state' in update_data:
        user_session.state = json.dumps(update_data['state'])

    user_session.last_activity = datetime.now(UTC)

    await user_session.save()

    return {'status': 'updated'}


@router.delete('/{session_id}')
async def delete_session(session_id: str):
    """End a session (logout)."""
    user_session = await UserSession.get_or_none(session_id=session_id)

    if user_session:
        user_session.is_active = False
        await user_session.save()

    return {'status': 'deleted'}


@router.get('/user/{user_id}')
async def get_user_sessions(user_id: int, current_user: User = Depends(get_current_user)):
    """Get all active sessions for a user."""
    if current_user.id != user_id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")

    sessions = await UserSession.filter(
        user_id=user_id,
        is_active=True,
        expires_at__gt=datetime.now(UTC),
    ).order_by('-last_activity')

    return [
        {
            'session_id': s.session_id,
            'created_at': s.created_at.isoformat() if s.created_at else None,
            'last_activity': s.last_activity.isoformat() if s.last_activity else None,
            'expires_at': s.expires_at.isoformat() if s.expires_at else None,
        }
        for s in sessions
    ]

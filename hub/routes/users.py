"""User resource routes"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..models import User
from ..dependencies import get_current_user
from ..database import get_session

router = APIRouter(prefix="/users", tags=["users"])


@router.get('', response_model=list[User])
async def get_users(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """
    Get all users
    """
    # require admin privileges:
    if current_user.role != 'admin':
        return {"error": "Unauthorized"}, 403

    users = session.exec(select(User).where(User.is_active)).all()
    return users


@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile

    Returns user info without sensitive fields
    """
    return {
        'id': current_user.id,
        'email': current_user.email,
        'first_name': current_user.first_name,
        'last_name': current_user.last_name,
        'role': current_user.role,
        'institution': current_user.institution,
        'created_at': current_user.created_at.isoformat()
    }

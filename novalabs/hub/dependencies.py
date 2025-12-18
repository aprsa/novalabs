"""
Shared FastAPI dependencies

This module contains all reusable dependencies that need FastAPI context
(Depends, HTTPException, etc). Keeping them separate from routes and auth
avoids circular imports.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .models import User
from .auth import verify_token

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency to get current authenticated user from JWT token

    Args:
        token: JWT token from Authorization header
        session: Database session

    Returns:
        User object for authenticated user

    Raises:
        HTTPException: 401 if token invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise credentials_exception

    user = await User.get_or_none(id=user_id_int)
    if user is None or not user.is_active:
        raise credentials_exception

    return user

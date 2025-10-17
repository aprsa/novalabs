"""Authentication routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from datetime import timedelta

from ..database import get_session
from ..auth import authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, hash_password
from ..models import User

router = APIRouter(tags=["auth"])


@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """
    OAuth2 compatible token login endpoint

    Returns JWT access token on successful authentication
    """
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={'sub': str(user.id)}, expires_delta=access_token_expires
    )

    return {
        'access_token': access_token,
        'token_type': 'bearer',
        'user': {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role
        }
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(registration: dict, session: Session = Depends(get_session)):
    """
    Register a new user account

    Creates a new user with 'student' role by default
    """
    # Check if email already exists
    existing_user = session.exec(select(User).where(User.email == registration['email'])).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email already registered'
        )

    # Validate password length
    if len(registration['password']) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Password must be at least 8 characters'
        )

    # Create new user
    hashed_password = hash_password(registration['password'])
    new_user = User(
        email=registration['email'],
        hashed_password=hashed_password,
        first_name=registration['first_name'],
        last_name=registration['last_name'],
        role='student',  # Default role
        institution=registration.get('institution')
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    return {
        'id': new_user.id,
        'email': new_user.email,
        'first_name': new_user.first_name,
        'last_name': new_user.last_name,
        'role': new_user.role,
        'rank': new_user.rank,
        'message': 'User registered successfully'
    }

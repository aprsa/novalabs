from datetime import datetime, timedelta, UTC
from typing import Optional
from jose import JWTError, jwt
from sqlmodel import Session, select
from .models import User
import toml
import bcrypt
import os

# Load config
config_path = os.path.join(os.path.dirname(__file__), 'config.toml')
config = toml.load(config_path)

SECRET_KEY = config['security']['secret_key']
ALGORITHM = config['security']['algorithm']
ACCESS_TOKEN_EXPIRE_MINUTES = config['security']['access_token_expire_minutes']


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def hash_password(password: str) -> str:
    """Hash a password"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload"""

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def authenticate_user(session: Session, email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password"""
    user = session.exec(select(User).where(User.email == email)).first()

    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None

    return user


def create_user(session: Session, email: str, password: str, first_name: str, last_name: str, role: str = "student", institution: Optional[str] = None) -> User:
    """Create a new user"""
    # Check if user exists
    exists = session.exec(select(User).where(User.email == email)).first()
    if exists:
        raise ValueError(f"User with email {email} already exists")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        role=role,
        institution=institution
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    return user

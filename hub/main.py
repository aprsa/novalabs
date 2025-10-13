from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
from sqlmodel import Session
from datetime import timedelta
import toml
import os

from .database import init_db, get_session
from .models import User
from . import auth as auth_module
from .auth import authenticate_user, create_access_token, verify_token, ACCESS_TOKEN_EXPIRE_MINUTES

# from .routes import api_router

# Load config
config_path = os.path.join(os.path.dirname(__file__), 'config.toml')
config = toml.load(config_path)


# Handle pre-API-startup and post-API-shutdown actions to set up/clean up
# (see https://fastapi.tiangolo.com/advanced/events/#lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-API-startup actions go here:
    init_db()
    print('NovaLabs database initialized')
    yield
    # Post-API-shutdown actions would go here

# Create FastAPI app
app = FastAPI(
    title="NovaLabs Hub",
    description="Central platform for astronomy lab management",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config['cors']['origins'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')


# Dependency to get current user from token
async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    print(f'debug: token={token}')
    payload = verify_token(token)
    print(f'debug: payload={payload}')
    if payload is None:
        raise credentials_exception

    user_id: int = payload.get('sub')
    print(f'debug: user_id={user_id}')
    if user_id is None:
        raise credentials_exception

    user = session.get(User, user_id)
    print('debug: user=', user)
    if user is None:
        raise credentials_exception

    return user

# Make get_current_user available to routes
auth_module.get_current_user = get_current_user


# ============================================================================
# Authentication Routes
# ============================================================================

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """Login endpoint - returns JWT token"""
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


@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return {
        'id': current_user.id,
        'email': current_user.email,
        'first_name': current_user.first_name,
        'last_name': current_user.last_name,
        'role': current_user.role,
        'institution': current_user.institution,
        'created_at': current_user.created_at.isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'service': 'novalabs-hub'
    }

# app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config['server']['host'], port=config['server']['port'])

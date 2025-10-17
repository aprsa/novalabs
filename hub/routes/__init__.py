"""API routes for Hub"""

from fastapi import APIRouter
from . import system, auth, users, labs, progress, admin

# Create main router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(labs.router)
api_router.include_router(progress.router)
api_router.include_router(admin.router)

__all__ = ['api_router']

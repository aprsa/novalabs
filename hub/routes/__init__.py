"""API routes for Hub"""

from fastapi import APIRouter
from . import system, auth, users, courses, labs, enrollments, assignments, sessions

# Create main router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(courses.router)
api_router.include_router(labs.router)
api_router.include_router(enrollments.router)
api_router.include_router(assignments.router)
api_router.include_router(sessions.router)

__all__ = ['api_router']

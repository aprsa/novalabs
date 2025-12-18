"""
NovaLabs Hub - Central authentication and lab management API.

The hub provides:
- User authentication and authorization (JWT-based)
- Lab progression tracking with prerequisites
- RESTful API for lab integrations
- Admin interfaces for user and lab management

Main Components:
    - routes/: FastAPI route definitions
    - models.py: User, session, and progress models
    - auth.py: Authentication utilities
    - database.py: Database initialization

API Structure:
    - /api/auth: Authentication endpoints
    - /api/users: User management
    - /api/labs: Lab information and access control
    - /api/progress: Progress tracking and submission
    - /api/sessions: Session management
    - /api/admin: Administrative functions
    - /api/system: Health checks and system info

Usage:
    Start the hub server:
        $ novalabs-hub

    Or programmatically:
        from novalabs.hub.main import app
        import uvicorn
        uvicorn.run(app, host='0.0.0.0', port=8100)
"""

__version__ = '0.2.0'

__all__ = ['__version__']

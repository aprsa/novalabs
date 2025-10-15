"""
Base class for all page implementations
Provides shared dependencies and helper methods
"""

import sys
import os
from typing import Optional

# Add parent directory to path so we can import hub modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nicegui import ui
from fastapi import Request
from client.sdk import HubClient, AuthenticationError, HubClientError

# Configuration
HUB_API_URL = os.environ.get('HUB_API_URL', 'http://localhost:8100')
SESSION_COOKIE_NAME = 'hub_token'

# Initialize Hub client
hub_client = HubClient(base_url=HUB_API_URL)


class PageBase:
    """
    Base class for all page implementations.
    Provides shared dependencies and helper methods.
    """

    # Class-level shared dependencies
    hub_client = hub_client
    HUB_API_URL = HUB_API_URL
    SESSION_COOKIE_NAME = SESSION_COOKIE_NAME

    @classmethod
    def get_current_user(cls, request: Request) -> Optional[dict]:
        """Get current user from session cookie"""
        token = request.cookies.get(cls.SESSION_COOKIE_NAME)
        if not token:
            return None

        cls.hub_client.token = token
        try:
            return cls.hub_client.get_current_user()
        except (AuthenticationError, HubClientError):
            return None

    @classmethod
    def require_auth(cls, request: Request):
        """Redirect to login if not authenticated"""
        user = cls.get_current_user(request)
        if not user:
            ui.navigate.to('/login')
            return None
        return user

    @classmethod
    def require_admin(cls, request: Request):
        """Redirect if not admin"""
        user = cls.require_auth(request)
        if not user:
            return None

        if user['role'] != 'admin':
            ui.navigate.to('/')
            return None

        return user

    @staticmethod
    def set_auth_cookie(token: str):
        """Set authentication cookie via JavaScript"""
        ui.run_javascript(f'''
            document.cookie = "{SESSION_COOKIE_NAME}={token}; max-age=28800; path=/; samesite=lax";
            window.location.href = "/";
        ''')

    @classmethod
    def logout(cls):
        """Clear authentication cookie and logout via SDK"""
        # Logout via SDK to clear token
        cls.hub_client.logout()

        # Clear cookie and redirect to login
        ui.run_javascript(f'''
            document.cookie = "{SESSION_COOKIE_NAME}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
            window.location.href = "/login";
        ''')

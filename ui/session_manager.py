# ui/session_manager.py
"""
Centralized session management for the UI.
Handles server-side session storage and token management.
"""
from typing import Optional, Dict, Any
from fastapi import Request
from nicegui import ui
import os

from client.sdk import SDKClient, AuthenticationError, SDKClientError

# Configuration
# TODO: use config.toml to read out the values
HUB_API_URL = os.environ.get('HUB_API_URL', 'http://localhost:8100')
SESSION_COOKIE_NAME = 'hub_session_id'


class SessionManager:
    """Manages server-side sessions and authentication state"""

    def __init__(self):
        self.hub_api_url = HUB_API_URL
        self.session_cookie_name = SESSION_COOKIE_NAME

    def create_client(self) -> SDKClient:
        """Create a new SDKClient instance"""
        return SDKClient(base_url=self.hub_api_url)

    def get_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from request cookie"""
        return request.cookies.get(self.session_cookie_name)

    def load_session(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Load session data from server using session_id cookie.
        Returns session data including token and state.
        """
        session_id = self.get_session_id(request)
        if not session_id:
            return None

        try:
            client = self.create_client()
            return client.get_session(session_id)
        except SDKClientError:
            return None

    def get_authenticated_client(self, request: Request) -> Optional[SDKClient]:
        """
        Get a SDKClient with token loaded from server session.
        Returns None if no valid session exists.
        """
        session_data = self.load_session(request)
        if not session_data or not session_data.get('token'):
            return None

        client = self.create_client()
        client.token = session_data['token']
        client.session.headers['Authorization'] = f'Bearer {session_data["token"]}'
        return client

    def get_current_user(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get current user info from server session"""
        client = self.get_authenticated_client(request)
        if not client:
            return None

        try:
            return client.get_current_user()
        except (AuthenticationError, SDKClientError):
            return None

    def login(self, email: str, password: str) -> str:
        """
        Login and create server-side session.
        Returns session_id.
        """
        client = self.create_client()

        # Step 1: Login and get token
        token = client.login(email, password)

        # Step 2: Create server-side session
        session_id = client.create_session()

        # Step 3: Store token in server session
        client.update_session(session_id, token=token)

        return session_id

    def logout(self, request: Request):
        """Delete server-side session"""
        session_id = self.get_session_id(request)
        if session_id:
            try:
                client = self.create_client()
                client.delete_session(session_id)
            except SDKClientError:
                pass

    def set_session_cookie(self, session_id: str):
        """Set session ID cookie (7 days expiration) and redirect"""
        ui.run_javascript(f'''
            document.cookie = "{self.session_cookie_name}={session_id}; max-age=604800; path=/; samesite=lax";
            window.location.href = "/";
        ''')

    def clear_session_cookie(self):
        """Clear session cookie and redirect to login"""
        ui.run_javascript(f'''
            document.cookie = "{self.session_cookie_name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
            window.location.href = "/login";
        ''')

    def save_state(self, request: Request, state: Dict[str, Any]):
        """Save arbitrary state to server-side session"""
        session_id = self.get_session_id(request)
        if not session_id:
            return

        client = self.get_authenticated_client(request)
        if client:
            try:
                client.update_session(session_id, state=state)
            except SDKClientError:
                pass

    def get_state(self, request: Request) -> Dict[str, Any]:
        """Get arbitrary state from server-side session"""
        session_data = self.load_session(request)
        if not session_data:
            return {}
        return session_data.get('state', {})

    def require_auth(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Require authentication, redirect to login if not authenticated.
        Returns user info if authenticated, None otherwise.
        """
        user = self.get_current_user(request)
        if not user:
            ui.navigate.to('/login')
            return None
        return user

    def require_admin(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Require admin role, redirect appropriately if not.
        Returns user info if admin, None otherwise.
        """
        user = self.require_auth(request)
        if not user:
            return None

        if user['role'] != 'admin':
            ui.navigate.to('/')
            return None

        return user


# Create singleton instance
session_manager = SessionManager()

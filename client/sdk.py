"""
Client SDK for NovaLabs Hub API

This client is used by lab UIs to interact with the hub
for authentication, user management, and lab progression tracking.
"""

import requests
from typing import Optional, Dict, Any, List


class SDKClientError(Exception):
    """Base exception for SDK client errors"""
    pass


class AuthenticationError(SDKClientError):
    """Raised when authentication fails"""
    pass


class SDKClient:
    """
    Client for interacting with NovaLabs Hub API

    Usage:
        sdk = SDKClient(base_url="http://localhost:8100")

        # Authenticate
        token = sdk.login(email="user@example.com", password="password")

        # Get current user
        user = sdk.get_current_user()

        # Get user's progress and rank
        progress = sdk.get_my_progress()

        # Check if user can access a lab
        can_access = sdk.check_lab_accessible(lab_ref="phoebe")

        # Start a lab
        sdk.start_lab(lab_ref="phoebe")

        # Complete a lab with score
        sdk.complete_lab(lab_ref="phoebe", score=85.5, bonus_points=10.0)
    """

    def __init__(self, base_url: str, token: Optional[str] = None):
        """
        Initialize SDK client

        Args:
            base_url: Base URL of Hub API (e.g., http://localhost:8100)
            token: Optional JWT token for authenticated requests
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session = requests.Session()

        if token:
            self.session.headers['Authorization'] = f'Bearer {token}'

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[Any, Any]:
        """
        Make HTTP request to Hub API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response JSON as dictionary

        Raises:
            SDKClientError: If request fails
        """
        url = f'{self.base_url}/{endpoint.lstrip("/")}'

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Handle both requests and httpx (TestClient) exceptions
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                if e.response.status_code == 401:
                    raise AuthenticationError('Authentication failed or token expired')
                raise SDKClientError(f'HTTP {e.response.status_code}: {e.response.text}')
            raise SDKClientError(f'Request failed: {str(e)}')

    def login(self, email: str, password: str) -> str:
        """
        Login and get JWT token

        Args:
            email: User email
            password: User password

        Returns:
            JWT access token

        Raises:
            AuthenticationError: If login fails
        """
        try:
            response = self._request('POST', '/token', data={'username': email, 'password': password})
            self.token = response['access_token']
            self.session.headers['Authorization'] = f'Bearer {self.token}'
            return self.token
        except SDKClientError:
            raise AuthenticationError("Invalid email or password")

    def register(self, email: str, password: str, first_name: str, last_name: str, institution: Optional[str] = None) -> Dict[str, Any]:
        """
        Register a new user account

        Args:
            email: User email
            password: User password
            first_name: User first name
            last_name: User last name
            institution: Optional institution name

        Returns:
            Dictionary with user information

        Raises:
            SDKClientError: If registration fails
        """
        return self._request('POST', '/register', json={
            'email': email,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
            'institution': institution
        })

    def logout(self) -> None:
        """
        Logout by clearing the token

        This clears the stored token and removes the Authorization header
        """
        self.token = None
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']

    def verify_token(self, token: Optional[str] = None) -> bool:
        """
        Verify if a token is valid

        Args:
            token: Token to verify (uses instance token if not provided)

        Returns:
            True if token is valid, False otherwise
        """
        test_token = token or self.token
        if not test_token:
            return False

        try:
            # Temporarily set token
            old_header = self.session.headers.get('Authorization')
            self.session.headers['Authorization'] = f'Bearer {test_token}'

            # Try to get current user
            self._request('GET', '/users/me')

            # Restore old header
            if old_header:
                self.session.headers['Authorization'] = old_header

            return True
        except (AuthenticationError, SDKClientError):
            if old_header:
                self.session.headers['Authorization'] = old_header
            return False

    def get_current_user(self) -> Dict[str, Any]:
        """
        Get current authenticated user

        Returns:
            User dictionary with id, email, first_name, last_name, role

        Raises:
            AuthenticationError: If not authenticated
        """
        return self._request('GET', '/users/me')

    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users (admin only)"""
        return self._request('GET', '/users')

    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user by ID"""
        return self._request('GET', f'/users/{user_id}')

    def create_user(
        self, email: str, password: str, first_name: str, last_name: str,
        role: str = "student", institution: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new user (admin only)"""
        return self._request(
            'POST',
            '/users',
            json={
                'email': email,
                'password': password,
                'first_name': first_name,
                'last_name': last_name,
                'role': role,
                'institution': institution
            }
        )

    def get_labs(self) -> List[Dict[str, Any]]:
        """Get all available labs"""
        return self._request('GET', '/labs')

    def get_lab(self, lab_ref: str) -> Dict[str, Any]:
        """Get lab by ref (e.g., 'phoebe')"""
        return self._request('GET', f'/labs/{lab_ref}')

    def register_lab(
        self, ref: str, name: str, description: str, ui_url: str, api_url: str,
        session_manager_url: str, sequence_order: int, category: Optional[str] = None,
        prerequisite_refs: Optional[List[str]] = None, has_bonus_challenge: bool = False,
        max_bonus_points: float = 0.0
    ) -> Dict[str, Any]:
        """
        Register a new lab (admin only)

        Args:
            ref: Unique lab identifier
            name: Lab display name
            description: Lab description
            ui_url: URL to lab UI
            api_url: URL to lab API
            session_manager_url: URL to lab session manager
            sequence_order: Position in lab sequence (0-based)
            category: Optional category (e.g., 'Earth', 'Solar System', 'Stars')
            prerequisite_refs: List of lab refs that must be completed first
            has_bonus_challenge: Whether lab has bonus challenge
            max_bonus_points: Maximum bonus points available

        Returns:
            Created lab dictionary

        Raises:
            SDKClientError: If registration fails
        """
        return self._request('POST', '/labs', json={
            'ref': ref,
            'name': name,
            'description': description,
            'ui_url': ui_url,
            'api_url': api_url,
            'session_manager_url': session_manager_url,
            'sequence_order': sequence_order,
            'category': category,
            'prerequisite_refs': prerequisite_refs or [],
            'has_bonus_challenge': has_bonus_challenge,
            'max_bonus_points': max_bonus_points
        })

    def check_lab_accessible(self, lab_ref: str) -> Dict[str, Any]:
        """
        Check if current user can access a lab

        Returns:
            Dictionary with:
            - accessible: bool
            - status: str ('locked', 'unlocked', 'in_progress', 'completed')
            - missing_prerequisites: List[str] (if locked)
        """
        return self._request('GET', f'/labs/{lab_ref}/accessible')

    # Progress tracking methods
    def get_my_progress(self) -> Dict[str, Any]:
        """
        Get current user's progress across all labs

        Returns:
            Dictionary with:
            - user: User info with rank and scores
            - labs: List of all labs with progress status
        """
        return self._request('GET', '/progress')

    def start_lab(self, lab_ref: str) -> Dict[str, Any]:
        """
        Start a lab (creates progress record if doesn't exist)

        Args:
            lab_ref: Lab identifier

        Returns:
            UserProgress record

        Raises:
            SDKClientError: If prerequisites not met or lab doesn't exist
        """
        return self._request('POST', f'/progress/lab/{lab_ref}/start')

    def complete_lab(
        self, lab_ref: str, score: float, bonus_points: float = 0.0
    ) -> Dict[str, Any]:
        """
        Complete a lab and submit score

        Args:
            lab_ref: Lab identifier
            score: Lab score (0-100)
            bonus_points: Bonus points earned

        Returns:
            Updated UserProgress with new rank info

        Raises:
            SDKClientError: If lab not started or invalid score
        """
        return self._request('POST', f'/progress/lab/{lab_ref}/complete', json={
            'score': score,
            'bonus_points': bonus_points
        })

    def get_user_progress(self, user_id: int) -> Dict[str, Any]:
        """
        Get any user's progress (admin/instructor only)

        Args:
            user_id: User ID to get progress for

        Returns:
            Dictionary with user info and lab progress
        """
        return self._request('GET', f'/admin/users/{user_id}/progress')

    def override_lab_score(
        self, user_id: int, lab_ref: str, score: float,
        bonus_points: Optional[float] = None, instructor_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Override a user's lab score (instructor/admin only)

        Args:
            user_id: User ID
            lab_ref: Lab identifier
            score: New score (0-100)
            bonus_points: Optional new bonus points
            instructor_notes: Optional notes about the override

        Returns:
            Updated UserProgress record
        """
        data = {'score': score}
        if bonus_points is not None:
            data['bonus_points'] = bonus_points
        if instructor_notes is not None:
            data['instructor_notes'] = instructor_notes

        return self._request(
            'PATCH',
            f'/admin/users/{user_id}/labs/{lab_ref}',
            json=data
        )

    def create_session(self) -> str:
        """Create a server-side session"""
        response = self._request('POST', '/sessions/create')
        return response['session_id']

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session data from server"""
        return self._request('GET', f'/sessions/{session_id}')

    def update_session(self, session_id: str, token: Optional[str] = None, state: Optional[dict] = None):
        """Update session on server"""
        data = {}
        if token:
            data['token'] = token
        if state:
            data['state'] = state
        return self._request('PATCH', f'/sessions/{session_id}', json=data)

    def delete_session(self, session_id: str):
        """Delete session (logout)"""
        return self._request('DELETE', f'/sessions/{session_id}')

    def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        return self._request('GET', f'/sessions/user/{user_id}')


# Example usage
if __name__ == "__main__":
    # Initialize client
    sdk = SDKClient(base_url="http://localhost:8100")

    # Login
    try:
        token = sdk.login(email="student@example.com", password="password")
        print("Logged in successfully")
        print(f"  Token: {token[:20]}...")

        # Get current user
        user = sdk.get_current_user()
        print(f"Current user: {user['first_name']} {user['last_name']}")
        print(f"  Role: {user['role']}")

        # Get my progress
        progress = sdk.get_my_progress()
        print(f"Current rank: {progress['user']['rank']}")
        print(f"  Total score: {progress['user']['total_score']}")
        print(f"  Total bonus: {progress['user']['total_bonus_points']}")

        # Get all labs
        labs = sdk.get_labs()
        print(f"Available labs: {len(labs)}")

        # Check if can access a specific lab
        lab_ref = "celestial-navigation"
        access = sdk.check_lab_accessible(lab_ref)
        if access['accessible']:
            print(f"Can access '{lab_ref}' (status: {access['status']})")

            # Start the lab (if not already started)
            if access['status'] == 'unlocked':
                sdk.start_lab(lab_ref)
                print(f"  Started lab '{lab_ref}'")

            # Complete the lab with score
            # sdk.complete_lab(lab_ref, score=85.5, bonus_points=10.0)
            # print(f"  Completed lab with score 85.5 + 10 bonus")
        else:
            print(f"Cannot access '{lab_ref}': {access.get('missing_prerequisites', [])}")

    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
    except SDKClientError as e:
        print(f"Error: {e}")

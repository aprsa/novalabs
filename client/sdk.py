"""
Client SDK for NovaLabs Hub API

This client is used by lab UIs to interact with the hub
for authentication, course management, and lab sessions.
"""

import requests
from typing import Optional, Dict, Any, List


class HubClientError(Exception):
    """Base exception for Hub client errors"""
    pass


class AuthenticationError(HubClientError):
    """Raised when authentication fails"""
    pass


class HubClient:
    """
    Client for interacting with NovaLabs Hub API

    Usage:
        hub = HubClient(base_url="http://localhost:8100")

        # Authenticate
        token = hub.login(email="user@example.com", password="password")

        # Get current user
        user = hub.get_current_user()

        # Check if user can access a lab
        access = hub.check_lab_access(user_id=1, lab_slug="phoebe")
    """

    def __init__(self, base_url: str, token: Optional[str] = None):
        """
        Initialize Hub client

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
            HubClientError: If request fails
        """
        url = f'{self.base_url}/{endpoint.lstrip("/")}'

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError('Authentication failed or token expired')
            raise HubClientError(f'HTTP {e.response.status_code}: {e.response.text}')
        except requests.exceptions.RequestException as e:
            raise HubClientError(f'Request failed: {str(e)}')

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
        except HubClientError:
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
            HubClientError: If registration fails
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
        except (AuthenticationError, HubClientError):
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

    def create_user(self, email: str, password: str, first_name: str, last_name: str, role: str = "student", institution: Optional[str] = None) -> Dict[str, Any]:
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

    def get_user_courses(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all courses for a user"""
        return self._request('GET', f'/users/{user_id}/courses')

    def get_courses(self) -> List[Dict[str, Any]]:
        """Get all available courses"""
        return self._request('GET', '/courses')

    def get_course(self, course_id: int) -> Dict[str, Any]:
        """Get course by ID"""
        return self._request('GET', f'/courses/{course_id}')

    def create_course(self, code: str, name: str, semester: str, instructor_id: int, institution: Optional[str] = None) -> Dict[str, Any]:
        """Create a new course (instructor/admin only)"""
        return self._request(
            'POST',
            '/courses',
            json={
                'code': code,
                'name': name,
                'semester': semester,
                'instructor_id': instructor_id,
                'institution': institution
            }
        )

    def get_labs(self) -> List[Dict[str, Any]]:
        """Get all available labs"""
        return self._request('GET', '/labs')

    def get_lab(self, lab_slug: str) -> Dict[str, Any]:
        """Get lab by slug (e.g., 'phoebe')"""
        return self._request('GET', f'/labs/{lab_slug}')

    def register_lab(self, slug: str, name: str, description: str, ui_url: str, api_url: str, session_manager_url: str) -> Dict[str, Any]:
        """
        Register a new lab (admin only)

        Args:
            slug: Unique lab identifier
            name: Lab display name
            description: Lab description
            ui_url: URL to lab UI
            api_url: URL to lab API
            session_manager_url: URL to lab session manager

        Returns:
            Created lab dictionary

        Raises:
            HubClientError: If registration fails
        """
        return self._request('POST', '/labs', json={
            'slug': slug,
            'name': name,
            'description': description,
            'ui_url': ui_url,
            'api_url': api_url,
            'session_manager_url': session_manager_url
        })

    def check_lab_access(self, user_id: int, lab_slug: str) -> Dict[str, Any]:
        """
        Check if user has access to a lab

        Returns:
            Dictionary with:
            - has_access: bool
            - course_id: Optional[int]
            - assignment_id: Optional[int]
            - reason: str (if no access)
        """
        return self._request('GET', f'/labs/{lab_slug}/access', params={'user_id': user_id})

    # Enrollment methods
    def get_enrollments(self, course_id: Optional[int] = None, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get enrollments, optionally filtered by course_id or user_id"""
        params = {}
        if course_id is not None:
            params['course_id'] = course_id
        if user_id is not None:
            params['user_id'] = user_id
        return self._request('GET', '/enrollments', params=params)

    def create_enrollment(self, user_id: int, course_id: int, role: str = 'student') -> Dict[str, Any]:
        """Create a new enrollment (instructor/admin only)"""
        return self._request('POST', '/enrollments', json={
            'user_id': user_id,
            'course_id': course_id,
            'role': role
        })

    def get_enrollment(self, enrollment_id: int) -> Dict[str, Any]:
        """Get enrollment by ID"""
        return self._request('GET', f'/enrollments/{enrollment_id}')

    def delete_enrollment(self, enrollment_id: int) -> Dict[str, Any]:
        """Delete an enrollment (instructor/admin only)"""
        return self._request('DELETE', f'/enrollments/{enrollment_id}')

    # Lab assignment methods
    def get_assignments(self, course_id: Optional[int] = None, lab_id: Optional[int] = None, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get lab assignments, optionally filtered"""
        params = {}
        if course_id is not None:
            params['course_id'] = course_id
        if lab_id is not None:
            params['lab_id'] = lab_id
        if is_active is not None:
            params['is_active'] = is_active
        return self._request('GET', '/assignments', params=params)

    def create_assignment(
        self, course_id: int, lab_id: int, title: str, due_date: Optional[str] = None,
        points_possible: Optional[float] = None, is_active: bool = True
    ) -> Dict[str, Any]:
        """Create a new lab assignment (instructor/admin only)"""
        return self._request('POST', '/assignments', json={
            'course_id': course_id,
            'lab_id': lab_id,
            'title': title,
            'due_date': due_date,
            'points_possible': points_possible,
            'is_active': is_active
        })

    def get_assignment(self, assignment_id: int) -> Dict[str, Any]:
        """Get assignment by ID"""
        return self._request('GET', f'/assignments/{assignment_id}')

    def update_assignment(self, assignment_id: int, **kwargs) -> Dict[str, Any]:
        """Update an assignment (instructor/admin only). Accepts: title, due_date, points_possible, is_active"""
        return self._request('PATCH', f'/assignments/{assignment_id}', json=kwargs)

    def delete_assignment(self, assignment_id: int) -> Dict[str, Any]:
        """Delete an assignment (instructor/admin only)"""
        return self._request('DELETE', f'/assignments/{assignment_id}')

    # Lab session methods
    def get_sessions(self, user_id: Optional[int] = None, lab_id: Optional[int] = None, course_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get lab sessions, optionally filtered"""
        params = {}
        if user_id is not None:
            params['user_id'] = user_id
        if lab_id is not None:
            params['lab_id'] = lab_id
        if course_id is not None:
            params['course_id'] = course_id
        return self._request('GET', '/sessions', params=params)

    def get_session(self, session_id: int) -> Dict[str, Any]:
        """Get session by ID"""
        return self._request('GET', f'/sessions/{session_id}')

    def create_lab_session(self, user_id: int, lab_slug: str, course_id: Optional[int] = None, assignment_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a new lab session for a user

        Returns:
            Lab session with external_session_id to use with lab's session manager
        """
        return self._request(
            'POST',
            '/lab-sessions',
            json={
                'user_id': user_id,
                'lab_slug': lab_slug,
                'course_id': course_id,
                'assignment_id': assignment_id
            }
        )

    def get_lab_session(self, session_id: int) -> Dict[str, Any]:
        """Get lab session by ID"""
        return self._request('GET', f'/lab-sessions/{session_id}')

    def get_user_lab_sessions(self, user_id: int, lab_slug: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all lab sessions for a user, optionally filtered by lab"""
        params = {}
        if lab_slug:
            params['lab_slug'] = lab_slug

        return self._request('GET', f'/users/{user_id}/lab-sessions', params=params)

    def update_lab_session_activity(self, session_id: int) -> Dict[str, Any]:
        """Update last activity timestamp for a session"""
        return self._request('PATCH', f'/lab-sessions/{session_id}/activity')

    def complete_lab_session(self, session_id: int) -> Dict[str, Any]:
        """Mark a lab session as completed"""
        return self._request('POST', f'/lab-sessions/{session_id}/complete')

    def get_user_grades(self, user_id: int, course_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all grades for a user, optionally filtered by course"""
        params = {}
        if course_id:
            params['course_id'] = course_id

        return self._request(
            'GET',
            f'/users/{user_id}/grades',
            params=params
        )

    def submit_grade(
        self, user_id: int, assignment_id: int, score: float, max_score: float,
        feedback: Optional[str] = None, auto_graded: bool = False
    ) -> Dict[str, Any]:
        """Submit a grade for a lab assignment"""
        return self._request(
            'POST',
            '/grades',
            json={
                'user_id': user_id,
                'assignment_id': assignment_id,
                'score': score,
                'max_score': max_score,
                'feedback': feedback,
                'auto_graded': auto_graded
            }
        )

    def get_or_create_lab_session(self, user_id: int, lab_slug: str, course_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get existing lab session or create a new one

        Checks for an active (not completed) session first.
        If none exists, creates a new one.
        """
        # Get existing sessions
        sessions = self.get_user_lab_sessions(user_id, lab_slug)

        # Find active session (not completed)
        for session in sessions:
            if session.get('completed_at') is None:
                # Update activity timestamp
                return self.update_lab_session_activity(session['id'])

        # No active session, create new one
        return self.create_lab_session(user_id, lab_slug, course_id)


# Example usage
if __name__ == "__main__":
    # Initialize client
    hub = HubClient(base_url="http://localhost:8100")

    # Login
    try:
        token = hub.login(email="admin@example.com", password="admin123")
        print("✓ Logged in successfully")
        print(f"  Token: {token[:20]}...")

        # Get current user
        user = hub.get_current_user()
        print(f"✓ Current user: {user['first_name']} {user['last_name']}")
        print(f"  Role: {user['role']}")

        # Get labs
        labs = hub.get_labs()
        print(f"✓ Available labs: {len(labs)}")

    except AuthenticationError as e:
        print(f"✗ Authentication failed: {e}")
    except HubClientError as e:
        print(f"✗ Error: {e}")

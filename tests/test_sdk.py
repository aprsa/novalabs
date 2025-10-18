"""
Tests for the Hub SDK client
"""
import pytest
from client.sdk import AuthenticationError


def test_sdk_login_success(sdk_client, test_user, client):
    """Test SDK login method"""
    # Override the session to use test client
    sdk_client.session = client

    token = sdk_client.login(email=test_user.email, password="testpass123")
    assert token is not None
    assert sdk_client.token == token
    assert "Authorization" in sdk_client.session.headers


def test_sdk_login_failure(sdk_client, client):
    """Test SDK login with wrong credentials"""
    sdk_client.session = client

    with pytest.raises(AuthenticationError):
        sdk_client.login(email="nobody@test.com", password="wrongpass")


def test_sdk_get_current_user(sdk_client, authenticated_client, test_user):
    """Test SDK getting current user"""
    sdk_client.session = authenticated_client
    sdk_client.token = "dummy"  # Already set in authenticated_client

    user = sdk_client.get_current_user()
    assert user["email"] == test_user.email
    assert user["first_name"] == test_user.first_name


def test_sdk_register(sdk_client, client):
    """Test SDK user registration"""
    sdk_client.session = client

    user = sdk_client.register(
        email="sdkuser@test.com",
        password="sdkpass123",
        first_name="SDK",
        last_name="User"
    )
    assert user["email"] == "sdkuser@test.com"
    assert user["role"] == "student"


def test_sdk_get_labs(sdk_client, authenticated_client, test_labs):
    """Test SDK getting labs list"""
    sdk_client.session = authenticated_client

    labs = sdk_client.get_labs()
    assert len(labs) == 3
    assert labs[0]["ref"] == "lab-1"


def test_sdk_get_lab(sdk_client, authenticated_client, test_labs):
    """Test SDK getting specific lab"""
    sdk_client.session = authenticated_client

    lab = sdk_client.get_lab("lab-1")
    assert lab["ref"] == "lab-1"
    assert lab["name"] == "First Lab"


def test_sdk_check_lab_accessible(sdk_client, authenticated_client, test_labs):
    """Test SDK checking lab accessibility"""
    sdk_client.session = authenticated_client

    access = sdk_client.check_lab_accessible("lab-1")
    assert access["accessible"] is True
    assert access["prerequisites_met"] is True


def test_sdk_get_my_progress(sdk_client, authenticated_client, test_labs):
    """Test SDK getting user progress"""
    sdk_client.session = authenticated_client

    progress = sdk_client.get_my_progress()
    assert "user" in progress
    assert "labs" in progress
    assert progress["user"]["rank"] == "dabbler"


def test_sdk_start_lab(sdk_client, authenticated_client, test_labs):
    """Test SDK starting a lab"""
    sdk_client.session = authenticated_client

    result = sdk_client.start_lab("lab-1")
    assert result["lab_ref"] == "lab-1"
    assert result["status"] == "in_progress"


def test_sdk_complete_lab(sdk_client, authenticated_client, test_labs):
    """Test SDK completing a lab"""
    sdk_client.session = authenticated_client

    # Start first
    sdk_client.start_lab("lab-1")

    # Complete
    result = sdk_client.complete_lab("lab-1", score=92.5, bonus_points=8.0)
    assert result["status"] == "completed"
    assert result["score"] == 92.5
    assert result["bonus_points"] == 8.0


def test_sdk_get_user_progress_as_admin(sdk_client, admin_client, test_user):
    """Test SDK getting another user's progress as admin"""
    sdk_client.session = admin_client

    progress = sdk_client.get_user_progress(test_user.id)
    assert progress['user']['email'] == test_user.email


def test_sdk_override_lab_score(sdk_client, admin_client, test_user, test_labs, session):
    """Test SDK overriding lab score as admin"""
    from hub.models import UserProgress, ProgressStatus

    # Create progress first
    progress = UserProgress(
        user_id=test_user.id,
        lab_id=test_labs[0].id,
        status=ProgressStatus.COMPLETED,
        score=70.0,
        bonus_points=0.0,
        attempts=1
    )
    session.add(progress)
    session.commit()

    sdk_client.session = admin_client

    result = sdk_client.override_lab_score(
        user_id=test_user.id,
        lab_ref="lab-1",
        score=95.0,
        bonus_points=10.0,
        instructor_notes="Excellent work!"
    )
    assert result["score"] == 95.0
    assert result["instructor_notes"] == "Excellent work!"


def test_sdk_logout(sdk_client, authenticated_client):
    """Test SDK logout"""
    sdk_client.session = authenticated_client
    sdk_client.token = "some_token"

    sdk_client.logout()
    assert sdk_client.token is None
    assert "Authorization" not in sdk_client.session.headers


def test_sdk_verify_token_valid(sdk_client, authenticated_client, test_user):
    """Test SDK token verification with valid token"""
    # Get a real token
    sdk_client.session = authenticated_client
    login_response = authenticated_client.post(
        "/token",
        data={"username": test_user.email, "password": "testpass123"}
    )
    token = login_response.json()["access_token"]

    is_valid = sdk_client.verify_token(token)
    assert is_valid is True


def test_sdk_verify_token_invalid(sdk_client, client):
    """Test SDK token verification with invalid token"""
    sdk_client.session = client

    is_valid = sdk_client.verify_token("invalid_token")
    assert is_valid is False


def test_sdk_error_handling(sdk_client, client):
    """Test SDK error handling for API errors"""
    sdk_client.session = client

    # Try to access protected endpoint without auth
    with pytest.raises(AuthenticationError):
        sdk_client.get_current_user()


def test_sdk_register_lab_as_admin(sdk_client, admin_client):
    """Test SDK registering a new lab"""
    sdk_client.session = admin_client

    lab = sdk_client.register_lab(
        ref="sdk-test-lab",
        name="SDK Test Lab",
        description="Created via SDK",
        ui_url="http://localhost:8999",
        api_url="http://localhost:8999/api",
        session_manager_url="http://localhost:8999/sessions",
        sequence_order=99,
        category="Test",
        prerequisite_refs=[],
        has_bonus_challenge=True,
        max_bonus_points=5.0
    )
    assert lab["ref"] == "sdk-test-lab"
    assert lab["max_bonus_points"] == 5.0


# ============================================================================
# Session Management Tests
# ============================================================================

def test_sdk_create_session(sdk_client, authenticated_client):
    """Test SDK creating a server-side session"""
    sdk_client.session = authenticated_client
    sdk_client.token = "dummy"

    session_id = sdk_client.create_session()
    assert session_id is not None
    assert len(session_id) > 0


def test_sdk_get_session(sdk_client, authenticated_client, test_user, session):
    """Test SDK getting session data"""
    from hub.models import UserSession
    from datetime import datetime, timedelta, UTC
    import secrets
    import json

    # Create a session in the database
    session_id = secrets.token_urlsafe(32)
    user_session = UserSession(
        session_id=session_id,
        user_id=test_user.id,
        token="test_token_12345",
        state=json.dumps({"key": "value"}),
        expires_at=datetime.now(UTC) + timedelta(days=7)
    )
    session.add(user_session)
    session.commit()

    # Get it via SDK
    sdk_client.session = authenticated_client
    sdk_client.token = "dummy"

    session_data = sdk_client.get_session(session_id)
    assert session_data["session_id"] == session_id
    assert session_data["user_id"] == test_user.id
    assert session_data["token"] == "test_token_12345"
    assert session_data["state"]["key"] == "value"
    assert "last_activity" in session_data


def test_sdk_update_session_token_only(sdk_client, authenticated_client, test_user, session):
    """Test SDK updating session token only"""
    from hub.models import UserSession
    from datetime import datetime, timedelta, UTC
    import secrets

    # Create a session
    session_id = secrets.token_urlsafe(32)
    user_session = UserSession(
        session_id=session_id,
        user_id=test_user.id,
        token="old_token",
        state="{}",
        expires_at=datetime.now(UTC) + timedelta(days=7)
    )
    session.add(user_session)
    session.commit()

    # Update token via SDK
    sdk_client.session = authenticated_client
    sdk_client.token = "dummy"

    result = sdk_client.update_session(session_id, token="new_token_12345")
    assert result["status"] == "updated"

    # Verify update
    session.refresh(user_session)
    assert user_session.token == "new_token_12345"


def test_sdk_update_session_state_only(sdk_client, authenticated_client, test_user, session):
    """Test SDK updating session state only"""
    from hub.models import UserSession
    from datetime import datetime, timedelta, UTC
    import secrets
    import json

    # Create a session
    session_id = secrets.token_urlsafe(32)
    user_session = UserSession(
        session_id=session_id,
        user_id=test_user.id,
        token="test_token",
        state=json.dumps({"old": "state"}),
        expires_at=datetime.now(UTC) + timedelta(days=7)
    )
    session.add(user_session)
    session.commit()

    # Update state via SDK
    sdk_client.session = authenticated_client
    sdk_client.token = "dummy"

    new_state = {"new": "state", "counter": 42}
    result = sdk_client.update_session(session_id, state=new_state)
    assert result["status"] == "updated"

    # Verify update
    session.refresh(user_session)
    assert json.loads(user_session.state) == new_state


def test_sdk_update_session_both(sdk_client, authenticated_client, test_user, session):
    """Test SDK updating both token and state"""
    from hub.models import UserSession
    from datetime import datetime, timedelta, UTC
    import secrets
    import json

    # Create a session
    session_id = secrets.token_urlsafe(32)
    user_session = UserSession(
        session_id=session_id,
        user_id=test_user.id,
        token="old_token",
        state=json.dumps({"old": "state"}),
        expires_at=datetime.now(UTC) + timedelta(days=7)
    )
    session.add(user_session)
    session.commit()

    # Update both via SDK
    sdk_client.session = authenticated_client
    sdk_client.token = "dummy"

    new_state = {"updated": "state"}
    result = sdk_client.update_session(session_id, token="new_token", state=new_state)
    assert result["status"] == "updated"

    # Verify both updated
    session.refresh(user_session)
    assert user_session.token == "new_token"
    assert json.loads(user_session.state) == new_state


def test_sdk_delete_session(sdk_client, authenticated_client, test_user, session):
    """Test SDK deleting a session"""
    from hub.models import UserSession
    from datetime import datetime, timedelta, UTC
    import secrets

    # Create a session
    session_id = secrets.token_urlsafe(32)
    user_session = UserSession(
        session_id=session_id,
        user_id=test_user.id,
        token="test_token",
        state="{}",
        expires_at=datetime.now(UTC) + timedelta(days=7)
    )
    session.add(user_session)
    session.commit()

    # Delete via SDK
    sdk_client.session = authenticated_client
    sdk_client.token = "dummy"

    result = sdk_client.delete_session(session_id)
    assert result["status"] == "deleted"

    # Verify session is inactive
    session.refresh(user_session)
    assert user_session.is_active is False


def test_sdk_get_user_sessions(sdk_client, authenticated_client, test_user, session):
    """Test SDK getting all sessions for a user"""
    from hub.models import UserSession
    from datetime import datetime, timedelta, UTC
    import secrets

    # Create multiple sessions
    session_ids = []
    for i in range(3):
        session_id = secrets.token_urlsafe(32)
        user_session = UserSession(
            session_id=session_id,
            user_id=test_user.id,
            token=f"token_{i}",
            state="{}",
            expires_at=datetime.now(UTC) + timedelta(days=7)
        )
        session.add(user_session)
        session_ids.append(session_id)
    session.commit()

    # Get all via SDK
    sdk_client.session = authenticated_client
    sdk_client.token = "dummy"

    sessions = sdk_client.get_user_sessions(test_user.id)
    assert len(sessions) == 3

    # Verify all sessions are returned
    returned_ids = [s["session_id"] for s in sessions]
    for sid in session_ids:
        assert sid in returned_ids


def test_sdk_get_user_sessions_as_admin(sdk_client, admin_client, test_user, session):
    """Test SDK admin getting another user's sessions"""
    from hub.models import UserSession
    from datetime import datetime, timedelta, UTC
    import secrets

    # Create session for test user
    session_id = secrets.token_urlsafe(32)
    user_session = UserSession(
        session_id=session_id,
        user_id=test_user.id,
        token="user_token",
        state="{}",
        expires_at=datetime.now(UTC) + timedelta(days=7)
    )
    session.add(user_session)
    session.commit()

    # Get as admin via SDK
    sdk_client.session = admin_client
    sdk_client.token = "dummy"

    sessions = sdk_client.get_user_sessions(test_user.id)
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == session_id


def test_sdk_session_lifecycle_complete(sdk_client, authenticated_client, test_user):
    """Test complete session lifecycle via SDK"""
    from client.sdk import SDKClientError
    
    sdk_client.session = authenticated_client
    sdk_client.token = "dummy"

    # 1. Create session
    session_id = sdk_client.create_session()
    assert session_id is not None

    # 2. Get session
    session_data = sdk_client.get_session(session_id)
    assert session_data["session_id"] == session_id

    # 3. Update session
    result = sdk_client.update_session(
        session_id,
        token="updated_token",
        state={"page": "dashboard"}
    )
    assert result["status"] == "updated"

    # 4. Verify update
    updated_data = sdk_client.get_session(session_id)
    assert updated_data["token"] == "updated_token"
    assert updated_data["state"]["page"] == "dashboard"

    # 5. Delete session
    delete_result = sdk_client.delete_session(session_id)
    assert delete_result["status"] == "deleted"

    # 6. Verify deletion - should return 404
    with pytest.raises(SDKClientError) as exc_info:
        sdk_client.get_session(session_id)
    assert "404" in str(exc_info.value)


def test_sdk_session_error_handling(sdk_client, authenticated_client):
    """Test SDK error handling for session operations"""
    from client.sdk import SDKClientError

    sdk_client.session = authenticated_client
    sdk_client.token = "dummy"

    # Try to get non-existent session
    with pytest.raises(SDKClientError) as exc_info:
        sdk_client.get_session("nonexistent_session_id")
    assert "404" in str(exc_info.value)

    # Try to update non-existent session
    with pytest.raises(SDKClientError) as exc_info:
        sdk_client.update_session("nonexistent_session_id", token="new_token")
    assert "404" in str(exc_info.value)


def test_sdk_get_user_sessions_access_denied(sdk_client, authenticated_client, test_instructor):
    """Test SDK user cannot access other user's sessions"""
    from client.sdk import SDKClientError

    sdk_client.session = authenticated_client
    sdk_client.token = "dummy"

    # Try to access instructor's sessions as student
    with pytest.raises(SDKClientError) as exc_info:
        sdk_client.get_user_sessions(test_instructor.id)
    assert "403" in str(exc_info.value)

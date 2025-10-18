"""
Tests for the user session API endpoints
"""
from datetime import datetime, timedelta, UTC
import json


def test_create_session(authenticated_client, test_user):
    """Test creating a new session"""
    response = authenticated_client.post("/sessions/create")
    assert response.status_code == 200
    
    data = response.json()
    assert "session_id" in data
    assert "expires_at" in data
    assert len(data["session_id"]) > 0


def test_create_session_unauthenticated(client):
    """Test creating session without authentication fails"""
    response = client.post("/sessions/create")
    assert response.status_code == 401


def test_get_session_by_id(authenticated_client, test_user, session):
    """Test retrieving a session by ID"""
    # Create a session first
    from hub.models import UserSession
    import secrets
    
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
    
    # Retrieve it
    response = authenticated_client.get(f"/sessions/{session_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["session_id"] == session_id
    assert data["user_id"] == test_user.id
    assert data["token"] == "test_token_12345"
    assert data["state"]["key"] == "value"
    assert "last_activity" in data


def test_get_session_not_found(authenticated_client):
    """Test getting non-existent session returns 404"""
    response = authenticated_client.get("/sessions/nonexistent_session_id")
    assert response.status_code == 404


def test_get_expired_session(authenticated_client, test_user, session):
    """Test getting expired session returns 404"""
    from hub.models import UserSession
    import secrets
    
    session_id = secrets.token_urlsafe(32)
    user_session = UserSession(
        session_id=session_id,
        user_id=test_user.id,
        token="expired_token",
        state="{}",
        expires_at=datetime.now(UTC) - timedelta(days=1)  # Expired
    )
    session.add(user_session)
    session.commit()
    
    response = authenticated_client.get(f"/sessions/{session_id}")
    assert response.status_code == 404


def test_get_inactive_session(authenticated_client, test_user, session):
    """Test getting inactive session returns 404"""
    from hub.models import UserSession
    import secrets
    
    session_id = secrets.token_urlsafe(32)
    user_session = UserSession(
        session_id=session_id,
        user_id=test_user.id,
        token="inactive_token",
        state="{}",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        is_active=False
    )
    session.add(user_session)
    session.commit()
    
    response = authenticated_client.get(f"/sessions/{session_id}")
    assert response.status_code == 404


def test_update_session_token(authenticated_client, test_user, session):
    """Test updating session token"""
    from hub.models import UserSession
    import secrets
    
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
    
    # Update token
    response = authenticated_client.patch(
        f"/sessions/{session_id}",
        json={"token": "new_token_12345"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "updated"
    
    # Verify update
    session.refresh(user_session)
    assert user_session.token == "new_token_12345"


def test_update_session_state(authenticated_client, test_user, session):
    """Test updating session state"""
    from hub.models import UserSession
    import secrets
    
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
    
    # Update state
    new_state = {"new": "state", "counter": 42}
    response = authenticated_client.patch(
        f"/sessions/{session_id}",
        json={"state": new_state}
    )
    assert response.status_code == 200
    
    # Verify update
    session.refresh(user_session)
    assert json.loads(user_session.state) == new_state


def test_update_session_both_token_and_state(authenticated_client, test_user, session):
    """Test updating both token and state simultaneously"""
    from hub.models import UserSession
    import secrets
    
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
    
    # Update both
    new_state = {"updated": "state"}
    response = authenticated_client.patch(
        f"/sessions/{session_id}",
        json={"token": "new_token", "state": new_state}
    )
    assert response.status_code == 200
    
    # Verify both updated
    session.refresh(user_session)
    assert user_session.token == "new_token"
    assert json.loads(user_session.state) == new_state


def test_update_session_not_found(authenticated_client):
    """Test updating non-existent session returns 404"""
    response = authenticated_client.patch(
        "/sessions/nonexistent_session",
        json={"token": "new_token"}
    )
    assert response.status_code == 404


def test_update_inactive_session_fails(authenticated_client, test_user, session):
    """Test updating inactive session returns 404"""
    from hub.models import UserSession
    import secrets
    
    session_id = secrets.token_urlsafe(32)
    user_session = UserSession(
        session_id=session_id,
        user_id=test_user.id,
        token="old_token",
        state="{}",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        is_active=False
    )
    session.add(user_session)
    session.commit()
    
    response = authenticated_client.patch(
        f"/sessions/{session_id}",
        json={"token": "new_token"}
    )
    assert response.status_code == 404


def test_delete_session(authenticated_client, test_user, session):
    """Test deleting/deactivating a session"""
    from hub.models import UserSession
    import secrets
    
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
    
    # Delete session
    response = authenticated_client.delete(f"/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    
    # Verify session is inactive
    session.refresh(user_session)
    assert user_session.is_active is False


def test_delete_nonexistent_session(authenticated_client):
    """Test deleting non-existent session returns success"""
    # Should not fail even if session doesn't exist
    response = authenticated_client.delete("/sessions/nonexistent_session")
    assert response.status_code == 200


def test_get_user_sessions(authenticated_client, test_user, session):
    """Test getting all sessions for a user"""
    from hub.models import UserSession
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
    
    # Get all user sessions
    response = authenticated_client.get(f"/sessions/user/{test_user.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 3
    
    # Verify all sessions are returned
    returned_ids = [s["session_id"] for s in data]
    for sid in session_ids:
        assert sid in returned_ids
    
    # Check structure
    assert "created_at" in data[0]
    assert "last_activity" in data[0]
    assert "expires_at" in data[0]


def test_get_user_sessions_excludes_expired(authenticated_client, test_user, session):
    """Test that expired sessions are not returned"""
    from hub.models import UserSession
    import secrets
    
    # Create active session
    active_id = secrets.token_urlsafe(32)
    active_session = UserSession(
        session_id=active_id,
        user_id=test_user.id,
        token="active_token",
        state="{}",
        expires_at=datetime.now(UTC) + timedelta(days=7)
    )
    session.add(active_session)
    
    # Create expired session
    expired_id = secrets.token_urlsafe(32)
    expired_session = UserSession(
        session_id=expired_id,
        user_id=test_user.id,
        token="expired_token",
        state="{}",
        expires_at=datetime.now(UTC) - timedelta(days=1)
    )
    session.add(expired_session)
    session.commit()
    
    # Get user sessions
    response = authenticated_client.get(f"/sessions/user/{test_user.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["session_id"] == active_id


def test_get_user_sessions_excludes_inactive(authenticated_client, test_user, session):
    """Test that inactive sessions are not returned"""
    from hub.models import UserSession
    import secrets
    
    # Create active session
    active_id = secrets.token_urlsafe(32)
    active_session = UserSession(
        session_id=active_id,
        user_id=test_user.id,
        token="active_token",
        state="{}",
        expires_at=datetime.now(UTC) + timedelta(days=7)
    )
    session.add(active_session)
    
    # Create inactive session
    inactive_id = secrets.token_urlsafe(32)
    inactive_session = UserSession(
        session_id=inactive_id,
        user_id=test_user.id,
        token="inactive_token",
        state="{}",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        is_active=False
    )
    session.add(inactive_session)
    session.commit()
    
    # Get user sessions
    response = authenticated_client.get(f"/sessions/user/{test_user.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["session_id"] == active_id


def test_get_user_sessions_requires_ownership(authenticated_client, test_user, test_instructor, session):
    """Test that users can only see their own sessions"""
    from hub.models import UserSession
    import secrets
    
    # Create session for instructor
    session_id = secrets.token_urlsafe(32)
    instructor_session = UserSession(
        session_id=session_id,
        user_id=test_instructor.id,
        token="instructor_token",
        state="{}",
        expires_at=datetime.now(UTC) + timedelta(days=7)
    )
    session.add(instructor_session)
    session.commit()
    
    # Try to access as student
    response = authenticated_client.get(f"/sessions/user/{test_instructor.id}")
    assert response.status_code == 403


def test_get_user_sessions_admin_can_access_any(admin_client, test_user, session):
    """Test that admins can see any user's sessions"""
    from hub.models import UserSession
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
    
    # Access as admin
    response = admin_client.get(f"/sessions/user/{test_user.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["session_id"] == session_id


def test_get_user_sessions_sorted_by_activity(authenticated_client, test_user, session):
    """Test that sessions are sorted by last activity (most recent first)"""
    from hub.models import UserSession
    import secrets
    
    # Create sessions with different activity times
    # Most recent session should be first (i=0), oldest last (i=2)
    session_data = []
    for i in range(3):
        session_id = secrets.token_urlsafe(32)
        user_session = UserSession(
            session_id=session_id,
            user_id=test_user.id,
            token=f"token_{i}",
            state="{}",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            last_activity=datetime.now(UTC) - timedelta(minutes=i)  # i=0 is most recent
        )
        session.add(user_session)
        session_data.append((session_id, i))  # Store with activity order
    session.commit()
    
    # Get sessions
    response = authenticated_client.get(f"/sessions/user/{test_user.id}")
    assert response.status_code == 200
    
    data = response.json()
    # Should be sorted by most recent activity first
    # i=0 (most recent), then i=1, then i=2 (oldest)
    assert data[0]["session_id"] == session_data[0][0]  # Most recent
    assert data[1]["session_id"] == session_data[1][0]  # Middle
    assert data[2]["session_id"] == session_data[2][0]  # Oldest


def test_session_updates_last_activity_on_get(authenticated_client, test_user, session):
    """Test that getting a session updates its last_activity timestamp"""
    from hub.models import UserSession
    import secrets
    import time
    
    session_id = secrets.token_urlsafe(32)
    old_activity = datetime.now(UTC) - timedelta(hours=1)
    user_session = UserSession(
        session_id=session_id,
        user_id=test_user.id,
        token="test_token",
        state="{}",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        last_activity=old_activity
    )
    session.add(user_session)
    session.commit()
    
    # Small delay to ensure timestamp difference
    time.sleep(0.01)
    
    # Get session - this should update last_activity
    response = authenticated_client.get(f"/sessions/{session_id}")
    assert response.status_code == 200
    
    # Check the returned data includes an updated timestamp
    data = response.json()
    # Parse the ISO format timestamp
    returned_activity_str = data["last_activity"]
    if returned_activity_str.endswith('Z'):
        returned_activity_str = returned_activity_str[:-1] + '+00:00'
    returned_activity = datetime.fromisoformat(returned_activity_str)
    
    # The returned activity should be more recent than the old activity
    # Compare as aware datetimes
    if old_activity.tzinfo is None:
        old_activity = old_activity.replace(tzinfo=UTC)
    if returned_activity.tzinfo is None:
        returned_activity = returned_activity.replace(tzinfo=UTC)
    
    assert returned_activity > old_activity


def test_session_lifecycle_complete(authenticated_client, test_user):
    """Test complete session lifecycle: create, use, update, delete"""
    # 1. Create session
    create_response = authenticated_client.post("/sessions/create")
    assert create_response.status_code == 200
    session_id = create_response.json()["session_id"]
    
    # 2. Get session
    get_response = authenticated_client.get(f"/sessions/{session_id}")
    assert get_response.status_code == 200
    assert get_response.json()["session_id"] == session_id
    
    # 3. Update session
    update_response = authenticated_client.patch(
        f"/sessions/{session_id}",
        json={"token": "updated_token", "state": {"page": "dashboard"}}
    )
    assert update_response.status_code == 200
    
    # 4. Verify update
    verify_response = authenticated_client.get(f"/sessions/{session_id}")
    verify_data = verify_response.json()
    assert verify_data["token"] == "updated_token"
    assert verify_data["state"]["page"] == "dashboard"
    
    # 5. Delete session
    delete_response = authenticated_client.delete(f"/sessions/{session_id}")
    assert delete_response.status_code == 200
    
    # 6. Verify deletion
    final_response = authenticated_client.get(f"/sessions/{session_id}")
    assert final_response.status_code == 404

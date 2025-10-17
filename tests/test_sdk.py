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

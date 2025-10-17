"""
Tests for lab endpoints (student/user facing)
"""


def test_get_labs_list(authenticated_client, test_labs):
    """Test getting list of all labs"""
    response = authenticated_client.get("/labs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # Check ordering by sequence
    assert data[0]["ref"] == "lab-1"
    assert data[1]["ref"] == "lab-2"
    assert data[2]["ref"] == "lab-3"


def test_get_lab_by_ref(authenticated_client, test_labs):
    """Test getting a specific lab by ref"""
    response = authenticated_client.get("/labs/lab-1")
    assert response.status_code == 200
    data = response.json()
    assert data["ref"] == "lab-1"
    assert data["name"] == "First Lab"
    assert data["sequence_order"] == 0
    assert data["has_bonus_challenge"] is True
    assert data["max_bonus_points"] == 10.0


def test_get_nonexistent_lab(authenticated_client):
    """Test getting a lab that doesn't exist"""
    response = authenticated_client.get("/labs/nonexistent")
    assert response.status_code == 404


def test_check_lab_accessible_first_lab(authenticated_client, test_labs):
    """Test that first lab is accessible (no prerequisites)"""
    response = authenticated_client.get(f"/labs/{test_labs[0].ref}/accessible")
    assert response.status_code == 200
    data = response.json()
    assert data['accessible'] is True
    assert data['prerequisites_met'] is True


def test_check_lab_accessible_locked(authenticated_client, test_labs, test_user, session):
    """Test that lab is locked when prerequisites not met"""
    response = authenticated_client.get(f"/labs/{test_labs[1].ref}/accessible")
    assert response.status_code == 200
    data = response.json()
    assert data['accessible'] is False
    assert data['prerequisites_met'] is False
    assert "lab-1" in data['missing_prerequisites']


def test_check_lab_accessible_after_completing_prereq(authenticated_client, test_labs, test_user, session):
    """Test that lab becomes accessible after completing prerequisite"""
    from hub.models import UserProgress, ProgressStatus

    # Complete lab-1
    progress = UserProgress(
        user_id=test_user.id,
        lab_id=test_labs[0].id,
        status=ProgressStatus.COMPLETED,
        score=85.0,
        bonus_points=5.0,
        attempts=1
    )
    session.add(progress)
    session.commit()

    # Check lab-2 is now accessible
    response = authenticated_client.get("/labs/lab-2/accessible")
    assert response.status_code == 200
    data = response.json()
    assert data['accessible'] is True
    assert data['prerequisites_met'] is True


def test_check_lab_accessible_unauthenticated(client, test_labs):
    """Test checking lab access without authentication"""
    response = client.get("/labs/lab-1/accessible")
    assert response.status_code == 401

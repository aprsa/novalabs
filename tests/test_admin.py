"""
Tests for admin endpoints (lab management and user progress management)
"""
from hub.models import UserProgress, ProgressStatus


# ============================================================================
# Lab Management Tests
# ============================================================================

def test_create_lab_as_admin(admin_client, test_labs):
    """Test creating a new lab as admin"""
    lab_data = {
        "ref": "new-lab",
        "name": "New Test Lab",
        "description": "A brand new lab",
        "sequence_order": 10,
        "category": "Stars",
        "prerequisite_refs": ["lab-3"],
        "ui_url": "http://localhost:8210",
        "api_url": "http://localhost:8210/api",
        "session_manager_url": "http://localhost:8210/sessions",
        "has_bonus_challenge": True,
        "max_bonus_points": 20.0
    }

    response = admin_client.post("/labs", json=lab_data)
    assert response.status_code == 200
    data = response.json()
    assert data["ref"] == "new-lab"
    assert data["name"] == "New Test Lab"
    assert data["max_bonus_points"] == 20.0


def test_create_lab_duplicate_ref(admin_client, test_labs):
    """Test creating a lab with duplicate ref fails"""
    lab_data = {
        "ref": "lab-1",  # Already exists
        "name": "Duplicate Lab",
        "description": "Should fail",
        "sequence_order": 20,
        "ui_url": "http://localhost:8220",
        "api_url": "http://localhost:8220/api",
        "session_manager_url": "http://localhost:8220/sessions",
    }

    response = admin_client.post("/labs", json=lab_data)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_create_lab_as_student_forbidden(authenticated_client):
    """Test that students cannot create labs"""
    lab_data = {
        "ref": "student-lab",
        "name": "Student Lab",
        "description": "Should be forbidden",
        "sequence_order": 30,
        "ui_url": "http://localhost:8230",
        "api_url": "http://localhost:8230/api",
        "session_manager_url": "http://localhost:8230/sessions",
    }

    response = authenticated_client.post("/labs", json=lab_data)
    assert response.status_code == 403


def test_update_lab_as_admin(admin_client, test_labs):
    """Test updating a lab as admin"""
    update_data = {
        "name": "Updated Lab Name",
        "description": "Updated description",
        "max_bonus_points": 25.0
    }

    response = admin_client.patch("/labs/lab-1", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Lab Name"
    assert data["description"] == "Updated description"
    assert data["max_bonus_points"] == 25.0
    assert data["ref"] == "lab-1"  # ref shouldn't change


def test_delete_lab_as_admin(admin_client, test_labs):
    """Test deleting a lab as admin"""
    response = admin_client.delete("/labs/lab-3")
    assert response.status_code == 200

    # Verify it's gone
    get_response = admin_client.get("/labs/lab-3")
    assert get_response.status_code == 404


def test_lab_prerequisite_validation(admin_client):
    """Test that prerequisite_refs is properly validated"""
    lab_data = {
        "ref": "test-prereqs",
        "name": "Test Prerequisites",
        "description": "Testing prereq validation",
        "sequence_order": 100,
        "prerequisite_refs": ["nonexistent-lab"],
        "ui_url": "http://localhost:8299",
        "api_url": "http://localhost:8299/api",
        "session_manager_url": "http://localhost:8299/sessions",
    }

    response = admin_client.post("/labs", json=lab_data)
    assert response.status_code == 400
    assert "prerequisite" in response.json()["detail"].lower()


# ============================================================================
# User Progress Management Tests
# ============================================================================

def test_get_user_progress_as_admin(admin_client, test_user, test_labs, session):
    """Test admin viewing another user's progress"""
    # Create some progress for test_user
    progress = UserProgress(
        user_id=test_user.id,
        lab_id=test_labs[0].id,
        status=ProgressStatus.COMPLETED,
        score=88.0,
        bonus_points=7.0,
        attempts=2
    )
    session.add(progress)
    session.commit()

    # Admin views user progress
    response = admin_client.get(f"/admin/users/{test_user.id}/progress")
    assert response.status_code == 200
    data = response.json()

    assert data["user"]["email"] == test_user.email
    assert "labs" in data
    # Should see the completed lab
    lab1_progress = next(lab for lab in data["labs"] if lab["lab"]["ref"] == "lab-1")
    assert lab1_progress["progress"]["status"] == "completed"
    assert lab1_progress["progress"]["score"] == 88.0


def test_get_user_progress_as_student_forbidden(authenticated_client, test_admin):
    """Test that students cannot view other users' progress"""
    response = authenticated_client.get(f"/admin/users/{test_admin.id}/progress")
    assert response.status_code == 403


def test_get_user_progress_nonexistent_user(admin_client):
    """Test viewing progress of non-existent user"""
    response = admin_client.get("/admin/users/99999/progress")
    assert response.status_code == 404


def test_override_lab_score_as_admin(admin_client, test_user, test_labs, session):
    """Test admin overriding a user's lab score"""
    # Create initial progress
    progress = UserProgress(
        user_id=test_user.id,
        lab_id=test_labs[0].id,
        status=ProgressStatus.COMPLETED,
        score=75.0,
        bonus_points=0.0,
        attempts=1
    )
    session.add(progress)
    test_user.total_score = 75.0
    session.add(test_user)
    session.commit()

    # Admin overrides score
    response = admin_client.patch(
        f"/admin/users/{test_user.id}/labs/lab-1",
        json={
            "score": 95.0,
            "bonus_points": 10.0,
            "instructor_notes": "Extra credit for outstanding work"
        }
    )
    assert response.status_code == 200
    data = response.json()

    assert data["score"] == 95.0
    assert data["bonus_points"] == 10.0


def test_override_lab_score_as_student_forbidden(authenticated_client, test_user, test_labs):
    """Test that students cannot override scores"""
    response = authenticated_client.patch(
        f"/admin/users/{test_user.id}/labs/lab-1",
        json={"score": 100.0}
    )
    assert response.status_code == 403


def test_override_recalculates_totals(admin_client, test_user, test_labs, session):
    """Test that score override recalculates user totals"""
    # Create initial progress
    progress = UserProgress(
        user_id=test_user.id,
        lab_id=test_labs[0].id,
        status=ProgressStatus.COMPLETED,
        score=70.0,
        bonus_points=0.0,
        attempts=1
    )
    session.add(progress)
    test_user.total_score = 70.0
    session.add(test_user)
    session.commit()

    # Override to higher score
    admin_client.patch(
        f"/admin/users/{test_user.id}/labs/lab-1",
        json={"score": 90.0, "bonus_points": 5.0}
    )

    # Refresh user from DB
    session.refresh(test_user)

    # Check totals were updated
    assert test_user.total_score == 90.0
    assert test_user.total_bonus_points == 5.0

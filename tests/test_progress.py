"""
Tests for progress tracking endpoints (student-facing)
"""
from hub.models import UserRank


def test_get_my_progress_empty(authenticated_client, test_labs):
    """Test getting progress when no labs started"""
    response = authenticated_client.get("/progress")
    assert response.status_code == 200
    data = response.json()

    assert "user" in data
    assert data["user"]["rank"] == "dabbler"
    assert data["user"]["total_score"] == 0.0
    assert data["user"]["total_bonus_points"] == 0.0

    assert "labs" in data
    assert len(data["labs"]) == 3

    # All labs should show status
    assert all('status' in lab['progress'] for lab in data['labs'])


def test_start_lab(authenticated_client, test_labs, test_user, session):
    """Test starting a lab"""
    response = authenticated_client.post('/progress/lab/lab-1/start')
    assert response.status_code == 200
    data = response.json()

    assert data['lab_ref'] == 'lab-1'
    assert data['status'] == 'in_progress'
    assert data['attempts'] == 1
    assert data['score'] == 0.0
    assert data['bonus_points'] == 0.0


def test_start_lab_locked(authenticated_client, test_labs):
    """Test starting a locked lab (missing prerequisites)"""
    response = authenticated_client.post("/progress/lab/lab-2/start")
    assert response.status_code == 403
    data = response.json()
    assert "prerequisite" in data["detail"].lower()


def test_start_lab_already_started(authenticated_client, test_labs, test_user, session):
    """Test starting a lab that's already in progress"""
    # Start lab first time
    authenticated_client.post("/progress/lab/lab-1/start")

    # Try to start again
    response = authenticated_client.post("/progress/lab/lab-1/start")
    assert response.status_code == 200
    data = response.json()

    # Should still show in_progress, attempts should remain 1
    assert data['status'] == 'in_progress'
    assert data['attempts'] == 1


def test_complete_lab_basic(authenticated_client, test_labs, test_user, session):
    """Test completing a lab with a score"""
    # Start the lab
    authenticated_client.post("/progress/lab/lab-1/start")
    
    # Complete it
    response = authenticated_client.post(
        "/progress/lab/lab-1/complete",
        json={"score": 85.5, "bonus_points": 5.0}
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "completed"
    assert data["score"] == 85.5
    assert data["bonus_points"] == 5.0
    assert "completed_at" in data


def test_complete_lab_updates_user_totals(authenticated_client, test_labs, test_user, session):
    """Test that completing labs updates user total score and rank"""
    # Start and complete lab-1
    authenticated_client.post("/progress/lab/lab-1/start")
    authenticated_client.post(
        "/progress/lab/lab-1/complete",
        json={"score": 90.0, "bonus_points": 10.0}
    )

    # Check user progress
    response = authenticated_client.get("/progress")
    data = response.json()

    assert data["user"]["total_score"] == 90.0
    assert data["user"]["total_bonus_points"] == 10.0
    assert data["user"]["rank"] == 'enthusiast'  # 1/3 labs = 33%


def test_complete_lab_not_started(authenticated_client, test_labs):
    """Test completing a lab that wasn't started"""
    response = authenticated_client.post(
        "/progress/lab/lab-1/complete",
        json={"score": 85.0, "bonus_points": 0.0}
    )
    assert response.status_code == 400
    assert "not started" in response.json()["detail"].lower()


def test_complete_lab_invalid_score(authenticated_client, test_labs):
    """Test completing a lab with invalid score"""
    authenticated_client.post("/progress/lab/lab-1/start")
    
    # Score > 100
    response = authenticated_client.post(
        "/progress/lab/lab-1/complete",
        json={"score": 150.0, "bonus_points": 0.0}
    )
    assert response.status_code == 400
    assert "score" in response.json()["detail"].lower()
    
    # Score < 0
    response = authenticated_client.post(
        "/progress/lab/lab-1/complete",
        json={"score": -10.0, "bonus_points": 0.0}
    )
    assert response.status_code == 400


def test_complete_lab_negative_bonus(authenticated_client, test_labs):
    """Test that negative bonus points are rejected"""
    authenticated_client.post("/progress/lab/lab-1/start")
    
    response = authenticated_client.post(
        "/progress/lab/lab-1/complete",
        json={"score": 85.0, "bonus_points": -5.0}
    )
    assert response.status_code == 400
    assert "bonus" in response.json()["detail"].lower()


def test_rank_calculation_progression(authenticated_client, test_labs, test_user, session):
    """Test rank progression as user completes labs"""
    # Complete all 3 labs with perfect scores
    for i, lab_ref in enumerate(["lab-1", "lab-2", "lab-3"]):
        if i > 0:
            # Need to complete previous labs first
            pass
        
        authenticated_client.post(f"/progress/lab/{lab_ref}/start")
        authenticated_client.post(
            f"/progress/lab/{lab_ref}/complete",
            json={"score": 100.0, "bonus_points": 0.0}
        )
    
    # Check final rank - 3/3 labs = 100% = master
    response = authenticated_client.get("/progress")
    data = response.json()

    assert data["user"]["total_score"] == 300.0
    assert data["user"]["rank"] == "master"


def test_progress_shows_correct_status(authenticated_client, test_labs, test_user, session):
    """Test that progress endpoint shows correct status for each lab"""
    # Complete lab-1
    authenticated_client.post("/progress/lab/lab-1/start")
    authenticated_client.post(
        "/progress/lab/lab-1/complete",
        json={"score": 80.0, "bonus_points": 0.0}
    )

    # Start lab-2 but don't complete
    authenticated_client.post("/progress/lab/lab-2/start")

    # Check progress
    response = authenticated_client.get("/progress")
    data = response.json()

    labs = {lab['lab']['ref']: lab['progress'] for lab in data['labs']}

    assert labs['lab-1']['status'] == "completed"
    assert labs['lab-2']['status'] == "in_progress"
    assert labs['lab-3']['status'] == "locked"  # Prerequisite not complete


def test_rank_thresholds():
    """Test rank calculation thresholds"""
    from hub.routes.progress import calculate_rank

    for i in range(0, 101, 5):
        rank = calculate_rank(100, i)
        print(f"Score: {i}, Rank: {rank}")

    # Test all thresholds
    assert calculate_rank(100, 0) == UserRank.DABBLER
    assert calculate_rank(100, 5) == UserRank.DABBLER
    assert calculate_rank(100, 10) == UserRank.HOBBYIST
    assert calculate_rank(100, 15) == UserRank.HOBBYIST
    assert calculate_rank(100, 30) == UserRank.ENTHUSIAST
    assert calculate_rank(100, 35) == UserRank.ENTHUSIAST
    assert calculate_rank(100, 45) == UserRank.EXPLORER
    assert calculate_rank(100, 50) == UserRank.EXPLORER
    assert calculate_rank(100, 60) == UserRank.APPRENTICE
    assert calculate_rank(100, 65) == UserRank.APPRENTICE
    assert calculate_rank(100, 80) == UserRank.RESEARCHER
    assert calculate_rank(100, 85) == UserRank.RESEARCHER
    assert calculate_rank(100, 95) == UserRank.MASTER
    assert calculate_rank(100, 100) == UserRank.MASTER


def test_multiple_attempts_increment(authenticated_client, test_labs, test_user, session):
    """Test that completing and restarting increments attempts"""
    # Complete lab once
    authenticated_client.post("/progress/lab/lab-1/start")
    authenticated_client.post(
        "/progress/lab/lab-1/complete",
        json={"score": 75.0, "bonus_points": 0.0}
    )

    # Start again (retake)
    response = authenticated_client.post("/progress/lab/lab-1/start")
    data = response.json()

    assert data["attempts"] == 2
    assert data["status"] == "in_progress"

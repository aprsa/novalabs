"""
Tests for authentication endpoints

Note: these tests rely on fixtures defined in conftest.py
"""


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_login_success(client, test_user):
    """Test successful login"""
    response = client.post(
        "/token",
        data={
            "username": test_user.email,
            "password": "testpass123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, test_user):
    """Test login with wrong password"""
    response = client.post(
        "/token",
        data={
            "username": test_user.email,
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


def test_login_nonexistent_user(client):
    """Test login with non-existent user"""
    response = client.post(
        "/token",
        data={
            "username": "nobody@test.com",
            "password": "password123"
        }
    )
    assert response.status_code == 401


def test_get_current_user_authenticated(authenticated_client, test_user):
    """Test getting current user info when authenticated"""
    response = authenticated_client.get("/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["first_name"] == test_user.first_name
    assert data["role"] == test_user.role
    assert data["rank"] == test_user.rank


def test_get_current_user_unauthenticated(client):
    """Test getting current user without authentication"""
    response = client.get("/users/me")
    assert response.status_code == 401


def test_get_current_user_invalid_token(client, random_jwt):
    """Test getting current user with invalid token"""
    client.headers["Authorization"] = f"Bearer {random_jwt}"
    response = client.get("/users/me")
    assert response.status_code == 401


def test_register_new_user(client):
    """Test user registration"""
    response = client.post(
        "/register",
        json={
            "email": "newuser@test.com",
            "password": "newpass123",
            "first_name": "New",
            "last_name": "User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["first_name"] == "New"
    assert data["role"] == "student"  # Default role
    assert data["rank"] == "dabbler"  # Default rank
    assert "hashed_password" not in data  # Password should not be returned


def test_register_duplicate_email(client, test_user):
    """Test registration with existing email"""
    response = client.post(
        "/register",
        json={
            "email": test_user.email,
            "password": "password123",
            "first_name": "Another",
            "last_name": "User"
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "already registered" in data["detail"].lower()


def test_token_includes_user_info(client, test_user):
    """Test that we can use token to access protected endpoints"""
    # Login
    login_response = client.post(
        "/token",
        data={
            "username": test_user.email,
            "password": "testpass123"
        }
    )
    token = login_response.json()["access_token"]
    
    # Use token
    client.headers["Authorization"] = f"Bearer {token}"
    user_response = client.get("/users/me")
    
    assert user_response.status_code == 200
    assert user_response.json()["email"] == test_user.email

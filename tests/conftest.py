"""
Pytest configuration and shared fixtures for testing
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
import json
import base64

from client.sdk import SDKClient
from hub.main import app
from hub.database import get_session
from hub.models import User, Lab, UserRole, UserRank
from hub.auth import hash_password


@pytest.fixture(name="engine")
def engine_fixture():
    """Create in-memory SQLite engine for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create database session for testing"""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(engine):
    """Create test client with test database"""
    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session):
    """Create a test student user"""
    user = User(
        email="student@test.com",
        hashed_password=hash_password("testpass123"),
        first_name="Test",
        last_name="Student",
        role=UserRole.STUDENT,
        rank=UserRank.DABBLER,
        total_score=0.0,
        total_bonus_points=0.0
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="test_admin")
def test_admin_fixture(session):
    """Create a test admin user"""
    admin = User(
        email="admin@test.com",
        hashed_password=hash_password("adminpass123"),
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        rank=UserRank.MASTER,
        total_score=1500.0,
        total_bonus_points=150.0
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


@pytest.fixture(name="test_instructor")
def test_instructor_fixture(session):
    """Create a test instructor user"""
    instructor = User(
        email="instructor@test.com",
        hashed_password=hash_password("instrpass123"),
        first_name="Jane",
        last_name="Instructor",
        role=UserRole.INSTRUCTOR,
        rank=UserRank.RESEARCHER,
        total_score=1200.0,
        total_bonus_points=100.0
    )
    session.add(instructor)
    session.commit()
    session.refresh(instructor)
    return instructor


@pytest.fixture(name="test_labs")
def test_labs_fixture(session):
    """Create test labs with sequence and prerequisites"""
    labs_data = [
        {
            'ref': 'lab-1',
            'name': 'First Lab',
            'description': 'Introduction lab',
            'sequence_order': 0,
            'category': 'Earth',
            'prerequisite_refs': json.dumps([]),
            'ui_url': 'http://localhost:8201',
            'api_url': 'http://localhost:8201/api',
            'session_manager_url': 'http://localhost:8201/sessions',
            'has_bonus_challenge': True,
            'max_bonus_points': 10.0
        },
        {
            'ref': 'lab-2',
            'name': 'Second Lab',
            'description': 'Requires lab-1',
            'sequence_order': 1,
            'category': 'Earth',
            'prerequisite_refs': json.dumps(['lab-1']),
            'ui_url': 'http://localhost:8202',
            'api_url': 'http://localhost:8202/api',
            'session_manager_url': 'http://localhost:8202/sessions',
            'has_bonus_challenge': False,
            'max_bonus_points': 0.0
        },
        {
            'ref': 'lab-3',
            'name': 'Third Lab',
            'description': 'Requires lab-2',
            'sequence_order': 2,
            'category': 'Solar System',
            'prerequisite_refs': json.dumps(['lab-2']),
            'ui_url': 'http://localhost:8203',
            'api_url': 'http://localhost:8203/api',
            'session_manager_url': 'http://localhost:8203/sessions',
            'has_bonus_challenge': True,
            'max_bonus_points': 15.0
        }
    ]

    labs = []
    for lab_data in labs_data:
        lab = Lab(**lab_data)
        session.add(lab)
        labs.append(lab)

    session.commit()
    for lab in labs:
        session.refresh(lab)

    return labs


@pytest.fixture(name="random_jwt")
def test_dummy_jwt_fixture():
    """Provide a dummy JWT token for testing"""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "test", "exp": 9999999999}).encode()).decode().rstrip('=')
    signature = base64.urlsafe_b64encode(b'fake_signature').decode().rstrip('=')
    return f"{header}.{payload}.{signature}"


@pytest.fixture(name="authenticated_client")
def authenticated_client_fixture(client, test_user):
    """Create authenticated test client"""
    response = client.post(
        "/token",
        data={"username": test_user.email, "password": "testpass123"}
    )
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture(name="admin_client")
def admin_client_fixture(client, test_admin):
    """Create authenticated admin client"""
    response = client.post(
        "/token",
        data={"username": test_admin.email, "password": "adminpass123"}
    )
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture(name="sdk_client")
def sdk_client_fixture(client):
    """Create SDK client pointing to test server"""
    sdk = SDKClient(base_url="http://testserver")
    sdk.session = client
    return sdk

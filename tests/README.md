# NovaLabs Hub Testing Guide

## Running Tests

### Install Test Dependencies

First, make sure you have pytest and pytest-cov installed:

```bash
pip install pytest pytest-cov
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=hub --cov=client --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::test_login_success

# Run with verbose output
pytest -v
```

## Test Structure

```ascii
tests/
├── __init__.py
├── conftest.py          # Shared fixtures and configuration
├── test_auth.py         # Authentication endpoint tests
├── test_labs.py         # Lab administration and access tests
├── test_progress.py     # Progress tracking endpoint tests
├── test_admin.py        # Admin operations (lab/progress management)
└── test_sdk.py          # SDK client tests
```

## Test Coverage

### Authentication Tests (`test_auth.py`)
- ✅ Health check endpoint
- ✅ Successful login
- ✅ Failed login (wrong password, non-existent user)
- ✅ Get current user (authenticated & unauthenticated)
- ✅ Invalid token handling
- ✅ User registration
- ✅ Duplicate email handling
- ✅ Token usage in protected endpoints

### Lab Discovery Tests (`test_labs.py`)
- ✅ Get labs list
- ✅ Get lab by ref (slug)
- ✅ Check lab accessibility
- ✅ Prerequisites validation
- ✅ Lab not found (404) handling
- ✅ Accessibility checks (locked vs unlocked)

### Progress Tracking Tests (`test_progress.py`)
- ✅ Get user progress (empty & with data)
- ✅ Start lab
- ✅ Complete lab
- ✅ Score validation (0-100 range)
- ✅ Bonus points validation
- ✅ Prerequisite enforcement
- ✅ Rank calculation and progression
- ✅ Total score recalculation
- ✅ Multiple attempts tracking
- ✅ Status tracking (locked/unlocked/in_progress/completed)
- ✅ Rank threshold testing
- ✅ Cannot start locked labs
- ✅ Progress state transitions

### Admin Operations Tests (`test_admin.py`)
- ✅ Create lab (admin only)
- ✅ Update lab (admin only)
- ✅ Delete lab (admin only)
- ✅ Permission checks (student vs admin)
- ✅ Duplicate ref handling
- ✅ Prerequisite validation on creation
- ✅ View user progress as admin
- ✅ Override lab scores
- ✅ Add instructor notes
- ✅ Recalculate totals after override
- ✅ Forbidden access for non-admins

### SDK Tests (`test_sdk.py`)
- ✅ Login/logout
- ✅ Token verification
- ✅ Get current user
- ✅ User registration
- ✅ Get labs & lab details
- ✅ Check lab accessibility
- ✅ Get progress
- ✅ Start lab
- ✅ Complete lab
- ✅ Admin operations (view progress, override scores)
- ✅ Error handling
- ✅ Register lab

## Test Fixtures

Key fixtures available in `conftest.py`:

### Database Fixtures
- `engine` - In-memory SQLite test database
- `session` - Database session for direct DB operations

### Client Fixtures
- `client` - FastAPI TestClient (unauthenticated)
- `authenticated_client` - Client with student auth token
- `admin_client` - Client with admin auth token
- `sdk_client` - HubClient SDK instance for testing

### User Fixtures
- `test_user` - Sample student user (student@test.com, UserRank.DABBLER)
- `test_admin` - Sample admin user (admin@test.com, UserRank.MASTER)
- `test_instructor` - Sample instructor user (instructor@test.com, UserRank.RESEARCHER)

### Lab Fixtures
- `test_labs` - 3 test labs with prerequisites:
  - `lab-1`: First Lab (no prerequisites, sequence 0, has bonus)
  - `lab-2`: Second Lab (requires lab-1, sequence 1)
  - `lab-3`: Third Lab (requires lab-2, sequence 2, has bonus)

### Utility Fixtures
- `random_jwt` - Dummy JWT token for testing invalid token scenarios

## Writing New Tests

Example test structure:

```python
def test_my_feature(authenticated_client, test_labs):
    """Test description"""
    # Arrange
    data = {"key": "value"}
    
    # Act
    response = authenticated_client.post("/endpoint", json=data)
    
    # Assert
    assert response.status_code == 200
    assert response.json()["key"] == "expected_value"
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines. They use in-memory SQLite databases, so no external dependencies are required.

## Test Data

All tests use isolated test data created by fixtures. No real database is touched. Each test gets a fresh database via the `engine` fixture.

## Debugging Tests

```bash
# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Show local variables on failure
pytest -l

# Run last failed tests only
pytest --lf
```

## Coverage Goals

Target: 90%+ code coverage for:
- `hub/routes/` - All endpoint handlers
- `hub/auth.py` - Authentication logic
- `client/sdk.py` - SDK methods

Current coverage: Run `pytest --cov=hub --cov=client --cov-report=term` to see.

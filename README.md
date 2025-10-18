# NovaLabs Hub

Central hub for Villanova's astronomy lab ecosystem - authentication, session management, and lab progression tracking.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

## Overview

NovaLabs Hub is the central landing page and authentication/session management platform for Villanova's astronomy lab ecosystem. It's a FastAPI-based service that manages users, lab access, and progress tracking across multiple independent astronomy lab applications.

### Key Features

- **Authentication & Authorization**: JWT-based auth with role management (student, instructor, admin)
- **Server-Side Session Management**: Persistent sessions with 7-day expiration and state storage
- **Lab Progression System**: Sequential lab unlocking based on prerequisites
- **Progress Tracking**: Track student progress with scores, bonus points, and rank progression
- **Progress Ranking**: 7-tier rank system (Dabbler → Hobbyist → Enthusiast → Apprentice → Explorer → Researcher → Master)
- **Lab Retakes**: Support for retaking completed labs to improve retention
- **Admin Dashboard**: Manage labs, view student progress, override scores
- **RESTful API**: Clean, documented API for lab integrations
- **Python SDK**: Client library (`SDKClient`) for lab UIs to interact with hub

## Architecture

```ascii
┌─────────────┐                            ┌─────────────┐
│  Lab UI 1   │       ┌────────────┐       │  Lab UI 2   │
└─────────────┘──────▶│  NovaLabs  │◀──────└─────────────┘
┌─────────────┐──────▶│     Hub    │◀──────┌─────────────┐
│  Lab UI 3   │       └────────────┘       │  Lab UI 4   │
└─────────────┘              │             └─────────────┘
                      ┌──────┴──────┐
                      │             │
                 ┌────▼────┐   ┌────▼───┐
                 │ SQLite  │   │  JWT   │
                 │   DB    │   │  Auth  │
                 └─────────┘   └────────┘
```

### Session Management

NovaLabs Hub uses server-side session management for persistent user sessions:

- **Session Creation**: After authentication, a server-side session is created with a unique session ID
- **Session Storage**: Sessions store JWT tokens, user state (JSON blob), and activity timestamps
- **Session Expiration**: Sessions automatically expire after 7 days of inactivity
- **Cookie-Based**: UI stores only the session ID in cookies (not the JWT token)
- **Multi-Session Support**: Users can have multiple active sessions (e.g., different browsers/devices)
- **Activity Tracking**: Last activity timestamp updates on each session access
- **State Persistence**: Session state survives browser restarts and crashes

**Flow**:
1. User logs in → receives JWT token
2. Create session → returns session_id
3. Store session_id in cookie
4. On each request → retrieve token from session using session_id
5. Use token for API authentication

## Installation

### Development Installation

```bash
# Clone the repository
git clone https://github.com/aprsa/novalabs.git
cd novalabs

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode with all dependencies
pip install -e ".[dev,ui]"
```

### Production Installation

```bash
pip install novalabs-hub
```

## Quick Start

### 1. Initialize the Database and Create Admin User

```bash
# Create admin account
novalabs-admin

# Seed the database with sample labs
novalabs-seed

# List all labs
novalabs-seed list
```

The `novalabs-admin` command will:
- Check if an admin user already exists
- If not, prompt you to enter admin details:
  - Email address
  - First and last name
  - Institution (optional)
  - Password (minimum 8 characters, with confirmation)

**Note:** To replace an existing admin, use `novalabs-admin --force` (requires password authentication + confirmation).

### 2. Start the Hub Server

```bash
# Using the entry point script
novalabs-hub

# Or directly with uvicorn
uvicorn hub.main:app --host 0.0.0.0 --port 8100 --reload
```

The API will be available at `http://localhost:8100`

### 3. Access the API Documentation

- **Interactive Docs**: http://localhost:8100/docs
- **ReDoc**: http://localhost:8100/redoc
- **OpenAPI JSON**: http://localhost:8100/openapi.json

### 4. Login and Get Token

Use the credentials you created in step 1:

```bash
curl -X POST "http://localhost:8100/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your-email@example.com&password=your-password"
```

## Usage

### Using the Python SDK

```python
from client.sdk import SDKClient

# Initialize client
sdk = SDKClient(base_url="http://localhost:8100")

# Login
token = sdk.login(email="student@example.com", password="password")

# Create a server-side session
session_id = sdk.create_session()
sdk.update_session(session_id, token=token, state={"page": "dashboard"})

# Get current user
user = sdk.get_current_user()
print(f"Logged in as: {user['first_name']} {user['last_name']}")

# Get user's progress
progress = sdk.get_my_progress()
print(f"Current rank: {progress['user']['rank']}")
print(f"Total score: {progress['user']['total_score']}")

# Get all available labs
labs = sdk.get_labs()
print(f"Available labs: {len(labs)}")

# Check if user can access a lab
access = sdk.check_lab_accessible("celestial-navigation")
if access['accessible']:
    # Start the lab
    sdk.start_lab("celestial-navigation")
    
    # Complete with score
    sdk.complete_lab("celestial-navigation", score=85.5, bonus_points=10.0)

# Manage sessions
user_sessions = sdk.get_user_sessions(user['id'])
print(f"Active sessions: {len(user_sessions)}")

# Logout (deactivates session)
sdk.delete_session(session_id)
```

### API Endpoints

#### Authentication

- `POST /token` - Login and get JWT token
- `POST /register` - Register new user account
- `GET /auth/verify` - Verify token validity

#### User Management

- `GET /users/me` - Get current user profile

#### Session Management

- `POST /sessions/create` - Create a new server-side session
- `GET /sessions/{session_id}` - Get session data (updates last_activity)
- `PATCH /sessions/{session_id}` - Update session token or state
- `DELETE /sessions/{session_id}` - Delete/deactivate session (logout)
- `GET /sessions/user/{user_id}` - Get all active sessions for a user

#### Labs

- `GET /labs` - List all labs (authenticated)
- `GET /labs/{lab_ref}` - Get specific lab details
- `GET /labs/{lab_ref}/accessible` - Check if user can access lab
- `POST /labs` - Create new lab (admin only)
- `PATCH /labs/{lab_ref}` - Update lab (admin only)
- `DELETE /labs/{lab_ref}` - Delete lab (admin only)

#### Progress

- `GET /progress` - Get user's progress across all labs
- `GET /progress/lab/{lab_ref}` - Get progress for specific lab
- `POST /progress/lab/{lab_ref}/start` - Start a lab
- `POST /progress/lab/{lab_ref}/complete` - Complete a lab with score

#### Admin

- `GET /admin/users/{user_id}/progress` - View any user's progress
- `PATCH /admin/users/{user_id}/labs/{lab_ref}` - Override lab score

## Data Model

### Core Entities

- **User**: Students, instructors, and admins with role-based access
- **Lab**: Individual lab activities with prerequisites and sequencing
- **UserProgress**: Tracks user progress through labs with scores and status
- **UserSession**: Server-side sessions with token storage, state, and expiration (7 days)

### User Ranks (Gamification)

Progress through labs unlocks higher ranks:

| Rank | Completion % |
|------|--------------|
| Dabbler | 0% |
| Hobbyist | ~14% |
| Enthusiast | ~28% |
| Apprentice | ~42% |
| Explorer | 60% |
| Researcher | ~71% |
| Master | ~85%+ |

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=hub --cov=client --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::test_login_success

# Run session tests
pytest tests/test_user_sessions.py -v
```

### Code Quality

```bash
# Format code with black
black hub client tests

# Lint with ruff
ruff check hub client tests

# Type check with mypy
mypy hub client
```

### Project Structure

```
novalabs/
├── hub/                    # Main hub application
│   ├── routes/            # API route handlers
│   │   ├── auth.py        # Authentication endpoints
│   │   ├── users.py       # User management
│   │   ├── labs.py        # Lab CRUD operations
│   │   ├── progress.py    # Progress tracking
│   │   ├── sessions.py    # Session management
│   │   ├── admin.py       # Admin operations
│   │   └── system.py      # System/health endpoints
│   ├── models.py          # Database models (User, Lab, UserProgress, UserSession)
│   ├── auth.py            # Authentication logic
│   ├── database.py        # Database setup
│   ├── dependencies.py    # FastAPI dependencies
│   ├── main.py           # FastAPI app
│   ├── create_admin.py   # Admin creation script
│   ├── seed_labs.py      # Database seeding
│   └── config.toml       # Configuration
├── client/                # Python SDK
│   └── sdk.py            # SDKClient - Hub API client
├── ui/                    # NiceGUI dashboards
│   ├── main.py           # Dashboard app entry point
│   ├── auth_pages.py     # Login/registration pages
│   ├── user_dash.py      # Student dashboard
│   ├── admin_dash.py     # Admin dashboard
│   └── session_manager.py # Session management singleton
├── tests/                 # Test suite
│   ├── conftest.py       # Shared fixtures
│   ├── test_auth.py      # Authentication tests
│   ├── test_labs.py      # Lab endpoint tests
│   ├── test_progress.py  # Progress tests
│   ├── test_admin.py     # Admin tests
│   ├── test_user_sessions.py # Session API tests
│   └── test_sdk.py       # SDK tests (including session wrappers)
├── pyproject.toml        # Project configuration
├── requirements.txt      # Dependencies
└── README.md            # This file
```

## Configuration

Configuration is stored in `hub/config.toml`:

```toml
[server]
host = "0.0.0.0"
port = 8100

[database]
path = "hub/data/novalabs.db"

[jwt]
secret_key = "your-secret-key-here"  # CHANGE IN PRODUCTION!
algorithm = "HS256"
access_token_expire_minutes = 180

[cors]
origins = [
    "http://localhost:3000",
    "http://localhost:8501"
]
```

⚠️ **Security Warning**: The default JWT secret key is for development only. Change it in production!

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0). See the LICENSE file for details.

## Authors

- **Andrej Prsa** - *Initial work* - [aprsa](https://github.com/aprsa)

## Acknowledgments

- Villanova University Department of Astrophysics and Planetary Science
- FastAPI framework
- SQLModel ORM

## Support

For issues and questions:
- GitHub Issues: https://github.com/aprsa/novalabs/issues
- Email: aprsa@villanova.edu

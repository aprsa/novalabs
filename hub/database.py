from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import toml
import os

# Import all models for automatic registration
from .models import User, Lab, UserProgress

# Load config
config_path = os.path.join(os.path.dirname(__file__), 'config.toml')
config = toml.load(config_path)

# Create engine
engine = create_engine(
    config['database']['url'],
    echo=config.get('debug', False),
    connect_args={"check_same_thread": False} if "sqlite" in config['database']['url'] else {}
)


def init_db():
    """Create all tables"""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Get database session for dependency injection"""
    with Session(engine) as session:
        yield session

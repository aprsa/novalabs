"""
NovaLabs Common Layer

Shared utilities and database management used by both hub and core.
"""

from .database import init_db, close_db, DatabaseContext
from .config import NovaLabsConfig

__all__ = [
    'init_db',
    'close_db',
    'DatabaseContext',
    'NovaLabsConfig',
]

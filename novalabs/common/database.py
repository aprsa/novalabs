"""
Database connection management for NovaLabs using Tortoise ORM.

Provides async database initialization and connection management.
"""

from typing import Optional
from tortoise import Tortoise

from .config import NovaLabsConfig

# Track initialization state
_initialized: bool = False


def get_tortoise_config(db_url: Optional[str] = None) -> dict:
    """
    Get Tortoise ORM configuration.

    Args:
        db_url: Optional database URL override

    Returns:
        Configuration dict for Tortoise.init()
    """

    config = NovaLabsConfig()
    if db_url is None:
        db_url = config.get_database_url()

    return {
        "connections": {
            "default": db_url,
        },
        "apps": {
            "models": {
                "models": [
                    "novalabs.hub.models",
                    "novalabs.core.models",
                    # "aerich.models",  # future expansion that would support migrations
                ],
                "default_connection": "default",
            },
        },
        "use_tz": True,
        "timezone": "UTC",
    }


async def init_db(db_url: Optional[str] = None, create_tables: bool = True) -> None:
    """
    Initialize the database connection.

    Args:
        db_url: Optional database URL override
        create_tables: Whether to create tables (default True)
    """
    global _initialized

    if _initialized:
        return

    config = get_tortoise_config(db_url)

    await Tortoise.init(config=config)

    if create_tables:
        await Tortoise.generate_schemas()

    _initialized = True


async def close_db() -> None:
    """Close database connections."""
    global _initialized

    if _initialized:
        await Tortoise.close_connections()
        _initialized = False


async def reset_db() -> None:
    """
    Reset the database (drop and recreate all tables).

    WARNING: This destroys all data!
    """
    global _initialized

    if _initialized:
        await Tortoise.close_connections()
        _initialized = False

    await init_db()

    # Drop and recreate
    await Tortoise.generate_schemas(safe=False)


def is_initialized() -> bool:
    """Check if database is initialized."""
    return _initialized


class DatabaseContext:
    """
    Context manager for standalone scripts that need database access.

    Usage:
        import asyncio

        async def main():
            async with DatabaseContext():
                # Do database operations
                lab = await Lab.get(id=1)

        asyncio.run(main())
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url

    async def __aenter__(self):
        await init_db(self.db_url)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await close_db()
        return False

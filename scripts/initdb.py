#!/usr/bin/env python3
"""
Initialize the NovaLabs database.

Creates all tables defined in hub and core models.

Usage:
    novalabs-initdb
    novalabs-initdb --drop  # Drop and recreate all tables
"""

import argparse
import asyncio
import sys

from tortoise import Tortoise

from novalabs.common.database import get_tortoise_config, init_db
from novalabs.common.config import NovaLabsConfig


async def main_async(drop: bool = False, verbose: bool = False):
    """Async main function."""
    config = NovaLabsConfig()
    db_url = config.get_database_url()

    print(f"Database URL: {db_url}")
    tortoise_config = get_tortoise_config(db_url)

    if drop:
        confirm = input(
            "WARNING: This will delete all data in the database.\n"
            "Type 'yes' to confirm: "
        )
        if confirm.lower() != 'yes':
            print("Aborted.")
            sys.exit(1)

        print("Dropping all tables...")
        await Tortoise.init(config=tortoise_config)

        # Get connection and drop all tables
        await Tortoise.generate_schemas(safe=False)
        await Tortoise.close_connections()
        print("Tables dropped and recreated.")
    else:
        print("Creating tables...")
        await init_db(db_url, create_tables=True)
        await Tortoise.close_connections()

    print("Database initialized successfully!")

    if verbose:
        # List models
        print("\nRegistered models:")
        for app_name, models in Tortoise.apps.items():
            for model_name in models:
                print(f"  - {app_name}.{model_name}")


def main():
    parser = argparse.ArgumentParser(
        description="Initialize the NovaLabs database"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all existing tables before creating (WARNING: destroys data)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output"
    )
    args = parser.parse_args()

    asyncio.run(main_async(drop=args.drop, verbose=args.verbose))


if __name__ == "__main__":
    main()

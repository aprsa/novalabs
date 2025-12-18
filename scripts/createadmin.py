#!/usr/bin/env python3
"""
Create an admin user for NovaLabs.

Usage:
    novalabs-createadmin
    novalabs-createadmin --email admin@example.com --password secret
"""

import argparse
import asyncio
import secrets
import string
import sys

import bcrypt

from novalabs.common.database import DatabaseContext
from novalabs.hub.models import User, UserRole


def generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def main_async(args):
    """Async main function."""
    # Get email
    email = args.email
    if not email:
        email = input("Admin email: ").strip()
        if not email:
            print("Error: Email is required")
            sys.exit(1)

    # Get first and last name
    first_name = args.first_name
    last_name = args.last_name

    if not first_name:
        first_name = input("First name: ").strip() or "n/a"
    if not last_name:
        last_name = input("Last name: ").strip() or "n/a"

    # Get password
    if args.generate_password:
        password = generate_password()
        print(f"Generated password: {password}")
    elif args.password:
        password = args.password
    else:
        import getpass
        password = getpass.getpass("Admin password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Error: Passwords do not match")
            sys.exit(1)

    if len(password) < 8:
        print("Error: Password must be at least 8 characters")
        sys.exit(1)

    async with DatabaseContext():
        existing = await User.get_or_none(email=email)

        if existing:
            if not args.force:
                print(f"Error: User with email '{email}' already exists")
                print("Use --force to update the existing user")
                sys.exit(1)

            # Update existing user
            existing.hashed_password = hash_password(password)
            existing.role = UserRole.ADMIN
            existing.first_name = first_name
            existing.last_name = last_name
            existing.is_active = True
            await existing.save()
            print(f"Updated existing user '{email}' to admin")
        else:
            # Create new user
            await User.create(
                email=email,
                hashed_password=hash_password(password),
                first_name=first_name,
                last_name=last_name,
                role=UserRole.ADMIN,
                is_active=True,
            )
            print(f"Created admin user '{email}'")

    print("Done!")


def main():
    parser = argparse.ArgumentParser(
        description="Create an admin user for NovaLabs"
    )
    parser.add_argument("--email", help="Admin email address")
    parser.add_argument("--password", help="Admin password")
    parser.add_argument("--generate-password", action="store_true", help="Generate a random password")
    parser.add_argument("--first-name", help="First name")
    parser.add_argument("--last-name", help="Last name")
    parser.add_argument("--force", action="store_true", help="Update existing user if email exists")
    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Install a lab into the user's NovaLabs directory.

Usage:
    novalabs-add-lab /path/to/lab-directory
    novalabs-add-lab /path/to/lab-directory --no-load
    novalabs-add-lab /path/to/lab-directory --force

This command:
1. Validates the lab structure
2. Copies it to ~/.novalabs/labs/{slug}/
3. Runs novalabs-loadlabs to register it (unless --no-load)
"""

import argparse
import asyncio
import shutil
import sys
from pathlib import Path

from novalabs.core.content.discovery import (
    validate_lab_structure,
    get_user_labs_dir,
    ensure_user_labs_dir,
)
from novalabs.common.database import init_db
from novalabs.core.content.lab2db import load_lab_content


def main():
    parser = argparse.ArgumentParser(
        description='Install a lab into NovaLabs user directory',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    novalabs-add-lab ./my-awesome-lab
    novalabs-add-lab /path/to/lab --no-load
    novalabs-add-lab ./lab --force
        """
    )
    
    parser.add_argument(
        'lab_path',
        type=str,
        help='Path to the lab directory to install'
    )
    
    parser.add_argument(
        '--no-load',
        action='store_true',
        help='Skip running novalabs-loadlabs after installation'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing lab without prompting'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Resolve lab path
    lab_path = Path(args.lab_path).resolve()
    
    if not lab_path.exists():
        print(f"Error: Path does not exist: {lab_path}", file=sys.stderr)
        sys.exit(1)
    
    if not lab_path.is_dir():
        print(f"Error: Path is not a directory: {lab_path}", file=sys.stderr)
        sys.exit(1)
    
    # Validate the lab
    print(f"Validating lab at: {lab_path}")
    info = validate_lab_structure(lab_path, source="user")
    
    # Report errors
    if info.errors:
        print("\n❌ Validation ERRORS (must fix before installing):")
        for err in info.errors:
            print(f"   {err.message}")
            if args.verbose:
                print(f"      Path: {err.path}")
        print("\nInstallation aborted due to errors.")
        sys.exit(1)
    
    # Report warnings
    if info.warnings:
        print("\n⚠️  Validation WARNINGS:")
        for warn in info.warnings:
            print(f"   {warn.message}")
            if args.verbose:
                print(f"      Path: {warn.path}")
        
        if not args.force:
            response = input("\nContinue with installation despite warnings? [y/N]: ")
            if response.lower() not in ('y', 'yes'):
                print("Installation cancelled.")
                sys.exit(0)
    
    # Check for existing lab
    user_labs_dir = ensure_user_labs_dir()
    target_dir = user_labs_dir / info.slug
    
    if target_dir.exists():
        if args.force:
            print(f"\n⚠️  Overwriting existing lab: {info.slug}")
            shutil.rmtree(target_dir)
        else:
            print(f"\n⚠️  Lab '{info.slug}' already exists at: {target_dir}")
            response = input("Overwrite? [y/N]: ")
            if response.lower() not in ('y', 'yes'):
                print("Installation cancelled.")
                sys.exit(0)
            shutil.rmtree(target_dir)
    
    # Copy lab to user directory
    print(f"\nCopying lab to: {target_dir}")
    shutil.copytree(lab_path, target_dir)
    
    print(f"✓ Lab '{info.slug}' installed successfully!")
    
    # Run loadlabs unless --no-load
    if not args.no_load:
        print("\nLoading lab into database...")
        try:
            asyncio.run(load_lab(target_dir))
            print("✓ Lab loaded into database")
        except Exception as e:
            print(f"⚠️  Warning: Failed to load lab: {e}", file=sys.stderr)
            print("   You can manually run: novalabs-loadlabs")
    else:
        print("\nSkipping database load (--no-load specified)")
        print("Run 'novalabs-loadlabs' to register the lab")
    
    print(f"\n🎉 Done! Lab '{info.slug}' is ready to use.")


async def load_lab(lab_path: Path):
    """Load a single lab into the database."""
    from novalabs.common.database import DatabaseContext
    from novalabs.core.content.discovery import validate_lab_structure
    from novalabs.core.content.lab2db import load_lab_content
    
    await init_db()
    
    info = validate_lab_structure(lab_path, source="user")
    if info.is_valid:
        async with DatabaseContext():
            await load_lab_content(info, force=True)
    else:
        raise ValueError(f"Lab validation failed: {[e.message for e in info.errors]}")


if __name__ == '__main__':
    main()

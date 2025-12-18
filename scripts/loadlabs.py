#!/usr/bin/env python3
"""
Discover and load labs into the database.

Usage:
    novalabs-loadlabs                  # Load from all paths (bundled + user)
    novalabs-loadlabs --bundled-only   # Only bundled labs
    novalabs-loadlabs --user-only      # Only user-installed labs
    novalabs-loadlabs --force          # Force reload even if unchanged
    novalabs-loadlabs --lab lab_slug   # Load a specific lab
    novalabs-loadlabs --validate-only  # Only validate, don't load

This command scans configured lab directories, validates lab structures,
and loads their content (quizzes, exercises) into the database.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from novalabs.common.database import DatabaseContext, init_db
from novalabs.common.config import NovaLabsConfig
from novalabs.core.content.discovery import (
    discover_all_labs,
    validate_lab_structure,
    get_bundled_labs_dir,
    get_user_labs_dir,
)
from novalabs.core.content.lab2db import load_lab_content


logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Discover and load labs into the NovaLabs database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Lab directories:
    Bundled:  {bundled}
    User:     {user}

Examples:
    novalabs-loadlabs                  # Load all labs
    novalabs-loadlabs --bundled-only   # Only bundled labs
    novalabs-loadlabs --user-only      # Only user-installed labs
    novalabs-loadlabs --lab slug       # Load a specific lab
    novalabs-loadlabs --force          # Force reload all
    novalabs-loadlabs --validate-only  # Validate without loading
        """.format(
            bundled=get_bundled_labs_dir(),
            user=get_user_labs_dir()
        )
    )
    
    parser.add_argument(
        '--bundled-only',
        action='store_true',
        help='Only load bundled labs (novalabs/labs/)'
    )
    
    parser.add_argument(
        '--user-only',
        action='store_true',
        help='Only load user-installed labs (~/.novalabs/labs/)'
    )

    parser.add_argument(
        '--lab',
        type=str,
        help='Load only a specific lab by slug'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reload even if content hash unchanged'
    )

    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate, do not load into database'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate conflicting options
    if args.bundled_only and args.user_only:
        print("Error: Cannot specify both --bundled-only and --user-only", file=sys.stderr)
        sys.exit(1)
    
    if args.lab and (args.bundled_only or args.user_only):
        print("Error: Cannot use --lab with --bundled-only or --user-only", file=sys.stderr)
        sys.exit(1)
    
    # Run async loading
    try:
        if args.lab:
            # Load specific lab
            asyncio.run(load_specific_lab(args.lab, args.force, args.validate_only))
        else:
            # Load based on flags
            include_bundled = not args.user_only
            include_user = not args.bundled_only
            
            asyncio.run(load_all(
                include_bundled=include_bundled,
                include_user=include_user,
                force=args.force,
                validate_only=args.validate_only
            ))
        
    except Exception as e:
        logger.exception(f"Error during lab loading: {e}")
        sys.exit(1)


async def load_specific_lab(lab_slug: str, force: bool, validate_only: bool):
    """Load or validate a specific lab by slug."""
    config = NovaLabsConfig()
    labs_dir = config.get_labs_directory()

    if not labs_dir.exists():
        print(f"Error: Labs directory not found: {labs_dir}")
        sys.exit(1)

    lab_path = labs_dir / lab_slug
    if not lab_path.exists():
        print(f"Error: Lab not found: {lab_path}")
        sys.exit(1)

    info = validate_lab_structure(lab_path)

    if not info.is_valid:
        print(f"Validation errors for {lab_slug}:")
        for err in info.errors:
            print(f"  ✗ {err.message}")
        sys.exit(1)

    if info.warnings:
        print(f"Warnings for {lab_slug}:")
        for warn in info.warnings:
            print(f"  ⚠ {warn.message}")

    if validate_only:
        print(f"✓ Lab '{lab_slug}' is valid")
        return

    # Initialize database and load
    await init_db()
    async with DatabaseContext():
        lab = await load_lab_content(info, force=force)
        if lab:
            print(f"✓ Loaded lab '{lab_slug}'")
        else:
            print(f"✗ Failed to load lab '{lab_slug}'")
            sys.exit(1)


async def load_all(include_bundled: bool, include_user: bool, force: bool, validate_only: bool):
    """Load all labs from configured paths."""
    
    # Initialize database
    print("Initializing database...")
    await init_db()
    
    # Discover labs
    print("\nDiscovering labs...")
    discovered = discover_all_labs(
        include_bundled=include_bundled,
        include_user=include_user
    )
    
    if not discovered:
        print("No labs found.")
        return
    
    print(f"Found {len(discovered)} lab(s)")
    
    # Validate all labs first
    valid_labs = {}
    invalid_count = 0
    
    print("\nValidating labs:")
    for slug, info in discovered.items():
        if info.is_valid:
            print(f"  ✓ {slug}")
            valid_labs[slug] = info
        else:
            print(f"  ✗ {slug}")
            invalid_count += 1
            for err in info.errors:
                print(f"      Error: {err.message}")
    
    if validate_only:
        summary = f"{len(valid_labs)} valid, {invalid_count} invalid"
        print(f"\n{summary}")
        sys.exit(0 if invalid_count == 0 else 1)
    
    if not valid_labs:
        print("\nNo valid labs to load.")
        sys.exit(1)
    
    # Load each valid lab
    print(f"\nLoading {len(valid_labs)} lab(s)...")
    results = {}
    
    async with DatabaseContext():
        for slug, info in valid_labs.items():
            try:
                lab = await load_lab_content(info, force=force)
                if lab:
                    print(f"  ✓ {slug}: {lab.title}")
                    results[slug] = lab
                else:
                    print(f"  ○ {slug}: unchanged (use --force to reload)")
                    results[slug] = "unchanged"
            except Exception as e:
                print(f"  ✗ {slug}: {e}")
                results[slug] = None
    
    # Summary
    loaded = sum(1 for v in results.values() if v is not None and v != "unchanged")
    unchanged = sum(1 for v in results.values() if v == "unchanged")
    failed = sum(1 for v in results.values() if v is None)
    
    print(f"\n{'='*50}")
    print(f"Summary: {loaded} loaded, {unchanged} unchanged, {failed} failed")
    
    if failed > 0:
        print("\nFailed labs:")
        for slug, result in results.items():
            if result is None:
                print(f"  - {slug}")
        sys.exit(1)


if __name__ == '__main__':
    main()

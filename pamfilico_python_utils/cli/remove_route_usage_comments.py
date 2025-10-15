#!/usr/bin/env python3
"""Remove Route Usage Comments - CLI Entry Point

Command-line interface for removing all ROUTE USAGES TOOL comment blocks from backend files.
Useful for cleaning up before re-running add_usage_comments tool.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli  # Python 3.11+
    except ImportError:
        tomli = None


def remove_all_blocks(lines: list) -> tuple:
    """Remove all ROUTE USAGES TOOL comment blocks (legacy and new format).

    Removes blocks with markers:
    - Legacy: # START: USAGES TOOL ... # END: USAGES TOOL
    - New: # START: ROUTE USAGES TOOL ... # END: ROUTE USAGES TOOL

    Args:
        lines: List of file lines

    Returns:
        Tuple of (modified_lines, blocks_removed_count)
    """
    blocks_removed = 0
    i = 0

    while i < len(lines):
        # Check for BOTH legacy and new markers
        if ('# START: USAGES TOOL' in lines[i] or
            '# START: ROUTE USAGES TOOL' in lines[i]):

            block_start = i
            block_end = None

            # Find matching END marker (legacy or new)
            for j in range(i + 1, min(len(lines), i + 10)):
                if ('# END: USAGES TOOL' in lines[j] or
                    '# END: ROUTE USAGES TOOL' in lines[j]):
                    block_end = j
                    break

            if block_end is not None:
                # Remove entire block
                del lines[block_start:block_end + 1]
                blocks_removed += 1
                # Don't increment i - continue from same position
            else:
                i += 1
        else:
            i += 1

    return lines, blocks_removed


def clean_file(file_path: Path, dry_run: bool = True) -> tuple:
    """Remove all comment blocks from a single file.

    Args:
        file_path: Path to Python file
        dry_run: If True, don't write changes

    Returns:
        Tuple of (blocks_removed, success)
    """
    if not file_path.exists():
        return 0, False

    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        original_count = len(lines)

        # Remove all blocks
        lines, blocks_removed = remove_all_blocks(lines)

        if blocks_removed > 0:
            if not dry_run:
                # Write back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
            return blocks_removed, True

        return 0, True

    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return 0, False


def load_config_from_pyproject() -> Optional[Dict[str, Any]]:
    """Load configuration from pyproject.toml if it exists

    Returns:
        Dictionary with config or None if not found
    """
    if tomli is None:
        return None

    # Look for pyproject.toml in current directory or parent directories
    cwd = Path.cwd()
    for path in [cwd] + list(cwd.parents):
        pyproject_path = path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                with open(pyproject_path, "rb") as f:
                    data = tomli.load(f)
                    # Try to get config from add_usage_comments section
                    config = data.get("tool", {}).get("add_usage_comments", {})
                    if config:
                        print(f"📋 Loaded config from: {pyproject_path}")
                        return config
            except Exception as e:
                print(f"Warning: Could not load {pyproject_path}: {e}")
                continue

    return None


def parse_arguments():
    """Parse command line arguments with pyproject.toml config support

    Command-line arguments override pyproject.toml settings.
    """
    # Load config from pyproject.toml
    config = load_config_from_pyproject()

    # Set defaults from config or hardcoded defaults
    default_backend = config.get("backend_path", "./") if config else "./"

    parser = argparse.ArgumentParser(
        description="Remove all ROUTE USAGES TOOL comment blocks from backend files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (preview changes)
  poetry run remove_route_usage_comments --dry-run

  # Actually remove all comment blocks
  poetry run remove_route_usage_comments

  # Custom backend path
  poetry run remove_route_usage_comments --backend-path ./my-backend

Configuration:
  Settings can be loaded from pyproject.toml [tool.add_usage_comments] section
        """,
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing files'
    )

    parser.add_argument(
        '--backend-path',
        type=str,
        default=default_backend,
        help=f'Path to backend directory (default: {default_backend})'
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()

    # Base paths
    cwd = Path.cwd()
    backend_base = cwd / args.backend_path

    if not backend_base.exists():
        print(f"❌ Backend directory not found: {backend_base}")
        sys.exit(1)

    print("🧹 Removing ROUTE USAGES TOOL Comment Blocks")
    print("=" * 50)
    print(f"Backend: {backend_base}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 50)
    print()

    # Find all Python files in the backend
    api_path = backend_base / "app" / "api"
    if not api_path.exists():
        print(f"⚠️  API path not found: {api_path}")
        print("Searching entire backend directory...")
        search_path = backend_base
    else:
        search_path = api_path

    python_files = list(search_path.rglob("*.py"))

    if not python_files:
        print(f"❌ No Python files found in {search_path}")
        sys.exit(1)

    print(f"Found {len(python_files)} Python files")
    print()

    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
        print()

    # Process each file
    total_blocks_removed = 0
    files_modified = 0
    files_processed = 0

    for file_path in sorted(python_files):
        rel_path = file_path.relative_to(backend_base)
        blocks_removed, success = clean_file(file_path, dry_run=args.dry_run)

        if success:
            files_processed += 1
            if blocks_removed > 0:
                files_modified += 1
                total_blocks_removed += blocks_removed
                status = "🔍 Would remove" if args.dry_run else "✅ Removed"
                print(f"  {status} {blocks_removed} block(s) from {rel_path}")

    # Summary
    print()
    print("=" * 50)
    print("📊 Summary")
    print("=" * 50)
    print(f"Files processed: {files_processed}")
    print(f"Files with blocks: {files_modified}")
    print(f"Total blocks removed: {total_blocks_removed}")

    if args.dry_run:
        print()
        print("⚠️  This was a DRY RUN. No files were modified.")
        print("Run without --dry-run to actually remove comment blocks.")
    else:
        print()
        print("✅ All comment blocks removed successfully!")

    print()


if __name__ == '__main__':
    main()

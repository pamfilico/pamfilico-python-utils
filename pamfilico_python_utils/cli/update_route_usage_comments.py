#!/usr/bin/env python3
"""Update Route Usage Comments - CLI Entry Point

Command-line interface that chains three operations:
1. Remove all existing route usage comment blocks
2. Generate fresh Flask route usage reports
3. Add updated comment blocks to route files

This ensures comment blocks are always in sync with current frontend usage.
"""

import argparse
import subprocess
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


def load_config_from_pyproject() -> Optional[Dict[str, Any]]:
    """Load configuration from pyproject.toml if it exists

    Looks for all three tool configurations:
    - [tool.remove_route_usage_comments]
    - [tool.flask_route_usage]
    - [tool.add_usage_comments]

    Returns:
        Dictionary with merged config or None if not found
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
                    tool_config = data.get("tool", {})

                    # Merge configs from all three tools
                    config = {}

                    # Remove config
                    if "remove_route_usage_comments" in tool_config:
                        config.update(tool_config["remove_route_usage_comments"])

                    # Flask route usage config
                    if "flask_route_usage" in tool_config:
                        config.update(tool_config["flask_route_usage"])

                    # Add usage comments config
                    if "add_usage_comments" in tool_config:
                        config.update(tool_config["add_usage_comments"])

                    if config:
                        print(f"📋 Loaded config from: {pyproject_path}")
                        return config
            except Exception as e:
                print(f"Warning: Could not load {pyproject_path}: {e}")
                continue

    return None


def run_command(command: list, description: str) -> bool:
    """Run a shell command and return success status

    Args:
        command: Command and arguments as list
        description: Human-readable description for output

    Returns:
        True if command succeeded, False otherwise
    """
    print(f"\n{'=' * 60}")
    print(f"📌 Step: {description}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=False  # Let output flow to terminal
        )
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {' '.join(command)}")
        print("   Make sure you're running this from the correct directory")
        return False


def parse_arguments():
    """Parse command line arguments

    This tool primarily uses pyproject.toml configuration.
    Command-line arguments are minimal since it chains other tools.
    """
    # Load config from pyproject.toml
    config = load_config_from_pyproject()

    parser = argparse.ArgumentParser(
        description="Update route usage comments by chaining three operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool performs three operations in sequence:

1. remove_route_usage_comments - Clean all existing comment blocks
2. flask_route_usage_report - Generate fresh usage reports
3. add_usage_comments - Add updated comment blocks

All operations use configuration from pyproject.toml.

Examples:
  # Run full update (uses pyproject.toml config)
  poetry run update_route_usage_comments

  # Dry run mode (preview changes without modifying files)
  poetry run update_route_usage_comments --dry-run

Configuration:
  Settings are loaded from pyproject.toml:

  [tool.remove_route_usage_comments]
  backend_path = "./"

  [tool.flask_route_usage]
  backend = "./"
  api_path = "app/api/v1"
  frontends = ["../frontend_carfast_manager_web", "../frontend_rentfast_landing"]
  frontend_src = "src"

  [tool.add_usage_comments]
  backend_path = "./"
  with_usage_report = "flask_routes_with_usage.md"
  without_usage_report = "flask_routes_without_usage.md"

Note: This tool must be run from a directory containing pyproject.toml
      with the required tool configurations.
        """,
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files (applies to add_usage_comments step)'
    )

    parser.add_argument(
        '--skip-remove',
        action='store_true',
        help='Skip the remove_route_usage_comments step (keep existing blocks)'
    )

    parser.add_argument(
        '--skip-report',
        action='store_true',
        help='Skip the flask_route_usage_report step (use existing reports)'
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()

    print("🔄 Update Route Usage Comments")
    print("=" * 60)
    print("This will chain three operations:")
    if not args.skip_remove:
        print("  1. Remove existing comment blocks")
    else:
        print("  1. [SKIPPED] Remove existing comment blocks")

    if not args.skip_report:
        print("  2. Generate fresh usage reports")
    else:
        print("  2. [SKIPPED] Generate fresh usage reports")

    print(f"  3. Add updated comment blocks {'(DRY RUN)' if args.dry_run else ''}")
    print("=" * 60)

    # Check if we're in a Poetry environment
    cwd = Path.cwd()
    if not (cwd / "pyproject.toml").exists():
        print("\n❌ Error: pyproject.toml not found in current directory")
        print("   This tool must be run from a directory with pyproject.toml")
        print("   containing [tool.remove_route_usage_comments], [tool.flask_route_usage],")
        print("   and [tool.add_usage_comments] configuration sections.")
        sys.exit(1)

    # Step 1: Remove existing comment blocks (unless skipped)
    if not args.skip_remove:
        success = run_command(
            ["poetry", "run", "remove_route_usage_comments"],
            "Remove existing comment blocks"
        )
        if not success:
            print("\n❌ Failed at step 1. Stopping execution.")
            sys.exit(1)
    else:
        print("\n⏭️  Skipping: Remove existing comment blocks")

    # Step 2: Generate fresh usage reports (unless skipped)
    if not args.skip_report:
        success = run_command(
            ["poetry", "run", "flask_route_usage_report"],
            "Generate fresh usage reports"
        )
        if not success:
            print("\n❌ Failed at step 2. Stopping execution.")
            sys.exit(1)
    else:
        print("\n⏭️  Skipping: Generate fresh usage reports")

    # Step 3: Add updated comment blocks
    command = ["poetry", "run", "add_usage_comments"]
    if args.dry_run:
        command.append("--dry-run")

    success = run_command(
        command,
        f"Add updated comment blocks {'(DRY RUN)' if args.dry_run else ''}"
    )
    if not success:
        print("\n❌ Failed at step 3. Stopping execution.")
        sys.exit(1)

    # Success!
    print("\n" + "=" * 60)
    print("🎉 Update completed successfully!")
    print("=" * 60)

    if args.dry_run:
        print("\n💡 This was a DRY RUN. To apply changes, run without --dry-run flag:")
        print("   poetry run update_route_usage_comments")
    else:
        print("\n✅ All comment blocks have been updated successfully")
        print("   - Old blocks removed")
        print("   - Fresh reports generated")
        print("   - New blocks added with current usage data")


if __name__ == '__main__':
    main()

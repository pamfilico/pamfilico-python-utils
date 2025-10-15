#!/usr/bin/env python3
"""Add Usage Comments - CLI Entry Point

Command-line interface for adding usage comments to Flask routes.
Reads flask_routes_with_usage.md and flask_routes_without_usage.md and adds comment blocks
above each route definition in the backend code.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli  # Python 3.11+
    except ImportError:
        tomli = None


@dataclass
class RouteUsage:
    """Represents usage information for a Flask route."""
    method: str
    path: str
    backend_file: str
    line_number: int
    function_name: str
    usage_locations: List[str]
    has_usage: bool


def parse_markdown_file(md_path: Path, has_usage: bool) -> List[RouteUsage]:
    """Parse a markdown file and extract route usage information."""
    routes = []

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by route sections (### headers)
    route_sections = re.split(r'\n### (DELETE|GET|PATCH|POST|PUT) ', content)

    for i in range(1, len(route_sections), 2):
        if i + 1 >= len(route_sections):
            break

        method = route_sections[i]
        section_content = route_sections[i + 1]

        # Extract route path
        path_match = re.match(r'`([^`]+)`', section_content)
        if not path_match:
            continue
        path = path_match.group(1)

        # Extract backend location
        backend_match = re.search(r'\*\*Backend Location:\*\* `([^:]+):(\d+)`', section_content)
        if not backend_match:
            continue
        backend_file = backend_match.group(1)
        line_number = int(backend_match.group(2))

        # Extract function name
        func_match = re.search(r'\*\*Function:\*\* `([^`]+)`', section_content)
        if not func_match:
            continue
        function_name = func_match.group(1)

        # Extract usage locations
        usage_locations = []
        if has_usage:
            # Find all frontend file references
            usage_pattern = r'^- `([^`]+)`\s*$'
            for line in section_content.split('\n'):
                match = re.match(usage_pattern, line.strip())
                if match:
                    usage_locations.append(match.group(1))

        # If marked as having usage but no locations found, treat as no usage
        # This handles routes in with_usage.md that have no actual frontend calls
        actual_has_usage = has_usage and len(usage_locations) > 0

        routes.append(RouteUsage(
            method=method,
            path=path,
            backend_file=backend_file,
            line_number=line_number,
            function_name=function_name,
            usage_locations=usage_locations,
            has_usage=actual_has_usage
        ))

    return routes


def generate_comment_block(route: RouteUsage) -> str:
    """Generate the comment block to add above the route definition."""
    if not route.has_usage:
        return (
            "# START: USAGES TOOL\n"
            "# No Usages: Please Check Before Deleting\n"
            "# END: USAGES TOOL\n"
        )

    # Build multi-line comment with usage locations
    # Use ./ prefix for workspace-relative paths that VSCode recognizes
    lines = ["# START: USAGES TOOL"]
    for location in route.usage_locations:
        # Extract file path and line number
        if ':' in location:
            file_path, line_num = location.rsplit(':', 1)
            # Format: ./path/to/file.ext:line (workspace-relative)
            lines.append(f"# ./{file_path}:{line_num}")
        else:
            lines.append(f"# ./{location}")
    lines.append("# END: USAGES TOOL")

    return '\n'.join(lines) + '\n'


def add_comments_to_file(backend_base: Path, routes_by_file: Dict[str, List[RouteUsage]], dry_run: bool = True):
    """Add usage comments to Flask route files."""

    for rel_path, routes in routes_by_file.items():
        file_path = backend_base / rel_path

        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        print(f"\n📝 Processing: {rel_path}")

        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Group routes by line number (multiple routes can point to same line)
        routes_by_line: Dict[int, List[RouteUsage]] = {}
        for route in routes:
            if route.line_number not in routes_by_line:
                routes_by_line[route.line_number] = []
            routes_by_line[route.line_number].append(route)

        # Sort line numbers in reverse order (so we don't mess up line numbers)
        routes_sorted = sorted(routes_by_line.items(), key=lambda x: x[0], reverse=True)

        modified = False
        for line_number, line_routes in routes_sorted:
            # Adjust for 0-based indexing
            decorator_line = line_number - 1

            if decorator_line < 0 or decorator_line >= len(lines):
                print(f"  ⚠️  Invalid line number {line_number}")
                continue

            # Scan backwards to find the start of decorators
            # The reported line is the @api.route() or @aade_bp.route() decorator
            # But there might be other decorators above it like @authenticatenext
            insert_line = decorator_line
            for i in range(decorator_line - 1, max(0, decorator_line - 10), -1):
                line_content = lines[i].strip()
                # Stop if we hit a non-decorator, non-comment, non-blank line
                if line_content and not line_content.startswith('@') and not line_content.startswith('#'):
                    # Found a non-decorator line, insert after it
                    insert_line = i + 1
                    break
                # If it's a decorator, continue scanning backwards
                if line_content.startswith('@'):
                    insert_line = i
            else:
                # We scanned all the way back or hit the start of file
                # Check if line 0 is a decorator
                if decorator_line > 0 and lines[0].strip().startswith('@'):
                    insert_line = 0

            # Merge all usage locations from all routes at this line
            all_usage_locations = []
            has_any_usage = False
            route_descriptions = []

            for route in line_routes:
                route_descriptions.append(f"{route.method} {route.path}")
                if route.has_usage:
                    has_any_usage = True
                    all_usage_locations.extend(route.usage_locations)

            # Remove duplicates while preserving order
            seen = set()
            unique_locations = []
            for loc in all_usage_locations:
                if loc not in seen:
                    seen.add(loc)
                    unique_locations.append(loc)

            # Check if comment already exists (look for START: USAGES TOOL marker)
            check_start = max(0, insert_line - 10)  # Check up to 10 lines above
            existing_start_line = None
            existing_end_line = None

            for i in range(check_start, insert_line):
                if '# START: USAGES TOOL' in lines[i]:
                    existing_start_line = i
                    # Now find the END marker
                    for j in range(i + 1, min(insert_line + 5, len(lines))):
                        if '# END: USAGES TOOL' in lines[j]:
                            existing_end_line = j
                            break
                    break

            # Remove existing comment block if found
            if existing_start_line is not None and existing_end_line is not None:
                # Remove the old block (all lines from start to end, inclusive)
                del lines[existing_start_line:existing_end_line + 1]
                # Adjust insert line since we removed lines above it
                insert_line = insert_line - (existing_end_line - existing_start_line + 1)
                action = "🔄 Replacing"
            else:
                action = "✅ Adding new"

            # Generate comment block for merged routes
            # Only treat as having usage if there are actual unique locations
            if has_any_usage and len(unique_locations) > 0:
                comment_lines = ["# START: USAGES TOOL"]
                for location in unique_locations:
                    if ':' in location:
                        location_file, line_num = location.rsplit(':', 1)
                        comment_lines.append(f"# ./{location_file}:{line_num}")
                    else:
                        comment_lines.append(f"# ./{location}")
                comment_lines.append("# END: USAGES TOOL")
                comment = '\n'.join(comment_lines) + '\n'
            else:
                comment = (
                    "# START: USAGES TOOL\n"
                    "# No Usages: Please Check Before Deleting\n"
                    "# END: USAGES TOOL\n"
                )

            # Insert the comment
            lines.insert(insert_line, comment)
            modified = True

            # Print status
            routes_str = ", ".join(route_descriptions)
            print(f"  {action} comment for: {routes_str}")

        # Write back to file
        if modified:
            if dry_run:
                print(f"  🔍 DRY RUN: Would modify {file_path}")
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"  💾 Saved changes to {file_path}")


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
    default_backend = config.get("backend_path", "backend_carfast") if config else "backend_carfast"
    default_with_usage = config.get("with_usage_report", "flask_routes_with_usage.md") if config else "flask_routes_with_usage.md"
    default_without_usage = config.get("without_usage_report", "flask_routes_without_usage.md") if config else "flask_routes_without_usage.md"

    parser = argparse.ArgumentParser(
        description="Add usage comments to Flask routes based on usage reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run with defaults from pyproject.toml
  poetry run add_usage_comments --dry-run

  # Apply changes (no dry-run flag)
  poetry run add_usage_comments

  # Custom backend path (overrides pyproject.toml)
  poetry run add_usage_comments --backend-path ./my-backend

  # Custom report files (overrides pyproject.toml)
  poetry run add_usage_comments \\
    --with-usage my_routes_with_usage.md \\
    --without-usage my_routes_without_usage.md

Configuration:
  Settings can be defined in pyproject.toml:

  [tool.add_usage_comments]
  backend_path = "backend_carfast"
  with_usage_report = "flask_routes_with_usage.md"
  without_usage_report = "flask_routes_without_usage.md"
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

    parser.add_argument(
        '--with-usage',
        type=str,
        default=default_with_usage,
        help=f'Path to routes with usage markdown file (default: {default_with_usage})'
    )

    parser.add_argument(
        '--without-usage',
        type=str,
        default=default_without_usage,
        help=f'Path to routes without usage markdown file (default: {default_without_usage})'
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()

    # Base paths
    cwd = Path.cwd()
    backend_base = cwd / args.backend_path

    with_usage_md = cwd / args.with_usage
    without_usage_md = cwd / args.without_usage

    # Check if files exist
    if not with_usage_md.exists():
        print(f"❌ File not found: {with_usage_md}")
        sys.exit(1)

    if not without_usage_md.exists():
        print(f"❌ File not found: {without_usage_md}")
        sys.exit(1)

    if not backend_base.exists():
        print(f"❌ Backend directory not found: {backend_base}")
        sys.exit(1)

    print("🔍 Parsing markdown files...")

    # Parse both markdown files
    routes_with_usage = parse_markdown_file(with_usage_md, has_usage=True)
    routes_without_usage = parse_markdown_file(without_usage_md, has_usage=False)

    all_routes = routes_with_usage + routes_without_usage

    print(f"✅ Found {len(routes_with_usage)} routes with usage")
    print(f"✅ Found {len(routes_without_usage)} routes without usage")
    print(f"✅ Total: {len(all_routes)} routes")

    # Group routes by file
    routes_by_file: Dict[str, List[RouteUsage]] = {}
    for route in all_routes:
        if route.backend_file not in routes_by_file:
            routes_by_file[route.backend_file] = []
        routes_by_file[route.backend_file].append(route)

    print(f"\n📂 Will modify {len(routes_by_file)} files")

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No files will be modified\n")
    else:
        print("\n⚠️  LIVE MODE - Files will be modified\n")

    # Add comments to files
    add_comments_to_file(backend_base, routes_by_file, dry_run=args.dry_run)

    print("\n✨ Done!")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Flask Route Usage Report - CLI Entry Point

Command-line interface for analyzing Flask routes and their frontend usage.
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

from pamfilico_python_utils.cli.flask_route_analyzer import FlaskRouteAnalyzer


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
                    config = data.get("tool", {}).get("flask_route_usage", {})
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
    default_backend = config.get("backend", "backend_carfast") if config else "backend_carfast"
    default_api_path = config.get("api_path", "app/api/v1") if config else "app/api/v1"
    default_frontends = config.get("frontends", ["frontend_carfast_manager_web", "frontend_rentfast_landing"]) if config else ["frontend_carfast_manager_web", "frontend_rentfast_landing"]
    default_frontend_src = config.get("frontend_src", "src") if config else "src"

    parser = argparse.ArgumentParser(
        description="Analyze Flask routes and their frontend usage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use defaults from pyproject.toml (if available) or hardcoded defaults
  poetry run flask_route_usage_report

  # Custom backend API path (overrides pyproject.toml)
  poetry run flask_route_usage_report --api-path app/api/v2

  # Custom frontend source paths (overrides pyproject.toml)
  poetry run flask_route_usage_report --frontend-src app/src

  # Custom backend and multiple frontends (overrides pyproject.toml)
  poetry run flask_route_usage_report --backend ./my-backend \\
    --frontends ./frontend1 ./frontend2

  # Everything custom
  poetry run flask_route_usage_report \\
    --backend ./my-backend \\
    --api-path api/routes \\
    --frontends ./web-app ./mobile-web \\
    --frontend-src source

Configuration:
  Settings can be defined in pyproject.toml:

  [tool.flask_route_usage]
  backend = "./"
  api_path = "app/api/v1"
  frontends = ["../frontend_carfast_manager_web", "../frontend_rentfast_landing"]
  frontend_src = "src"
        """,
    )

    parser.add_argument(
        "--backend",
        type=str,
        default=default_backend,
        help=f"Backend root directory (default: {default_backend})",
    )

    parser.add_argument(
        "--api-path",
        type=str,
        default=default_api_path,
        help=f"API subdirectory within backend (default: {default_api_path})",
    )

    parser.add_argument(
        "--frontends",
        nargs="+",
        default=default_frontends,
        help=f"Frontend root directories (default: {' '.join(default_frontends)})",
    )

    parser.add_argument(
        "--frontend-src",
        type=str,
        default=default_frontend_src,
        help=f"Source subdirectory within each frontend (default: {default_frontend_src})",
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    # Parse command line arguments
    args = parse_arguments()

    # Define paths relative to current working directory
    cwd = Path.cwd()

    backend_root = cwd / args.backend
    frontend_roots = [cwd / f for f in args.frontends]

    print("Flask Route Usage Analyzer")
    print("=" * 50)
    print(f"Backend: {backend_root}")
    print(f"API Path: {backend_root / args.api_path}")
    for frontend in frontend_roots:
        print(f"Frontend: {frontend}")
        print(f"  Source: {frontend / args.frontend_src}")
    print("=" * 50)
    print()

    # Verify paths exist
    if not backend_root.exists():
        print(f"❌ Error: Backend path not found: {backend_root}")
        sys.exit(1)

    # Create analyzer with custom paths
    analyzer = FlaskRouteAnalyzer(
        backend_root=str(backend_root),
        frontend_roots=[str(f) for f in frontend_roots],
        api_subpath=args.api_path,
        frontend_src_subpath=args.frontend_src,
    )

    # Extract routes and usages
    print("📡 Extracting Flask routes from backend...")
    analyzer.extract_routes()

    print("\n🔍 Extracting API calls from frontend...")
    analyzer.extract_frontend_usages()

    print("\n🔗 Matching routes to usages...")

    # Generate split reports
    print("\n📝 Generating reports...")
    analyzer.generate_split_reports()

    print("\n✅ Done!")


if __name__ == "__main__":
    main()

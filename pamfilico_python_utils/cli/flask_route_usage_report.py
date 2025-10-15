#!/usr/bin/env python3
"""Flask Route Usage Report - CLI Entry Point

Command-line interface for analyzing Flask routes and their frontend usage.
"""

import argparse
import sys
from pathlib import Path

from pamfilico_python_utils.cli.flask_route_analyzer import FlaskRouteAnalyzer


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Analyze Flask routes and their frontend usage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use defaults (current monorepo structure)
  poetry run flask_route_usage_report

  # Custom backend API path
  poetry run flask_route_usage_report --api-path app/api/v2

  # Custom frontend source paths
  poetry run flask_route_usage_report --frontend-src app/src

  # Custom backend and multiple frontends
  poetry run flask_route_usage_report --backend ./my-backend \\
    --frontends ./frontend1 ./frontend2

  # Everything custom
  poetry run flask_route_usage_report \\
    --backend ./my-backend \\
    --api-path api/routes \\
    --frontends ./web-app ./mobile-web \\
    --frontend-src source
        """,
    )

    parser.add_argument(
        "--backend",
        type=str,
        default="backend_carfast",
        help="Backend root directory (default: backend_carfast)",
    )

    parser.add_argument(
        "--api-path",
        type=str,
        default="app/api/v1",
        help="API subdirectory within backend (default: app/api/v1)",
    )

    parser.add_argument(
        "--frontends",
        nargs="+",
        default=["frontend_carfast_manager_web", "frontend_rentfast_landing"],
        help="Frontend root directories (default: frontend_carfast_manager_web frontend_rentfast_landing)",
    )

    parser.add_argument(
        "--frontend-src",
        type=str,
        default="src",
        help="Source subdirectory within each frontend (default: src)",
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

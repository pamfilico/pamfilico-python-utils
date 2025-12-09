# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the Pamfilico Python Utils package - a collection of utility functions and helpers for common tasks in Python web applications, particularly Flask with SQLAlchemy. The package provides mixins, decorators, authentication utilities, storage clients, and CLI tools for route analysis.

## Development Commands

### Installation
```bash
# Install dependencies
poetry install
```

### Deployment
```bash
# Simple patch bump with commit
./deploy.sh -m "fix: bug description"

# Minor version bump for new features  
./deploy.sh -m "feat: new feature" -i minor

# Major version bump for breaking changes
./deploy.sh -m "feat!: breaking change" -i major

# Dry run to preview changes
./deploy.sh -d -m "test message"
```

The deploy script automatically handles git commits, version bumping with commitizen, tagging, and pushing to GitHub.

## Architecture & Structure

### Module Organization

1. **pamfilico_python_utils/sqlalchemy/** - Database mixins and utilities
   - `mixins.py`: DateTimeMixin for timestamp fields
   - `auth.py`: NextAuth.js compatible authentication mixins (User, Session, Account, VerificationToken)
   - `utils.py`: UUID generation utilities

2. **pamfilico_python_utils/flask/** - Flask-specific utilities
   - `auth.py`: JWT authentication decorator with role-based scopes
   - `auth_next.py`: NextAuth.js-compatible authentication for Flask
   - `pagination.py`: Collection decorator for automatic pagination
   - `errors.py`: Custom error classes and Flask error handlers
   - `responses.py`: Standard response formatting utilities

3. **pamfilico_python_utils/storage/** - Cloud storage clients
   - `s3_digitalocean.py`: DigitalOceanSpacesClient for S3-compatible object storage

4. **pamfilico_python_utils/cli/** - Command-line tools
   - `flask_route_analyzer.py`: Core analyzer class for route usage detection
   - `flask_route_usage_report.py`: Generate markdown reports of route usage
   - `add_usage_comments.py`: Add usage comments to Flask routes
   - `remove_route_usage_comments.py`: Remove usage comments from routes
   - `update_route_usage_comments.py`: Update existing comments

### Key Design Patterns

1. **Authentication Flow**: The package provides both traditional JWT auth (`jwt_authenticator_with_scopes`) and NextAuth.js-compatible auth (`authenticatenext`). The NextAuth auth requires one-time configuration via `configure_authenticatenext()` during app initialization.

2. **Pagination Pattern**: The `collection` decorator automatically handles pagination, search, and sorting for SQLAlchemy queries. It expects decorators to return Query objects (not executed results).

3. **CLI Tool Configuration**: All CLI tools support both command-line arguments and pyproject.toml configuration under `[tool.<tool_name>]` sections.

4. **Route Analysis**: The FlaskRouteAnalyzer uses regex parsing to extract Flask routes and frontend API calls, performing fuzzy matching for dynamic routes.

## Version Management

The package uses semantic versioning managed by commitizen. Version is tracked in:
- `pyproject.toml`: Main version source under `[tool.poetry]` and `[tool.commitizen]`
- Git tags: Format `v{version}` (e.g., v0.3.2)

## Testing Considerations

Currently no test suite exists. When adding tests:
- Use pytest as the test runner
- Place tests in a `tests/` directory
- Test database mixins with SQLAlchemy test fixtures
- Mock external services (DigitalOcean Spaces, JWT tokens)
- Test CLI tools with temporary file fixtures
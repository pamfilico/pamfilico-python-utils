# Pamfilico Python Utils

Python utility functions and helpers for common tasks.

## Installation

Install directly from GitHub using Poetry (note the `git+` prefix):

```bash
poetry add git+https://github.com/pamfilico/pamfilico-python-utils.git
```

**Important:** The `git+` prefix is required for Poetry/pip to recognize this as a git repository URL.

## For Maintainers: Deployment

This package includes an automated deployment script that handles:
- Git commits (optional)
- Version bumping (patch/minor/major)
- Git tagging
- Pushing to GitHub

### Quick Deploy

```bash
# Simple patch bump with commit message
./deploy.sh -m "fix: bug fix description"

# Feature addition (minor version bump)
./deploy.sh -m "feat: new feature" -i minor

# Breaking change (major version bump)
./deploy.sh -m "feat!: breaking change" -i major

# Skip commit, just bump and push
./deploy.sh -s -i patch

# Dry run to preview
./deploy.sh -d -m "test message"
```

### Deploy Script Options

- `-m, --message <msg>` - Commit message (required if uncommitted changes exist)
- `-i, --increment <type>` - Version increment: `patch` (default), `minor`, or `major`
- `-s, --skip-commit` - Skip git commit step (only bump version and push)
- `-d, --dry-run` - Preview what would be done without executing
- `-h, --help` - Show help message

### After Deployment

Update the package in projects using it:

```bash
cd backend_carfast
poetry update pamfilico-python-utils
```

## Features

- **SQLAlchemy Mixins**: Ready-to-use mixins for common database patterns
  - `DateTimeMixin`: Automatic `created_at` and `updated_at` timestamp fields
  - NextAuth.js mixins for user authentication (User, Session, Account, VerificationToken)
  - `generate_uuid()`: UUID generation utility

- **Flask Utilities**: Authentication, error handling, and response formatting
  - `jwt_authenticator_with_scopes`: JWT authentication decorator with role-based access
  - `validate_uuid_params`: UUID parameter validation decorator
  - `admin_required`: Admin token authentication decorator
  - `collection`: Automatic pagination decorator with search and sorting
  - `standard_response`: Consistent API response formatting
  - Custom error classes and Flask error handlers
  - JWE token encryption/decryption utilities

- **Storage Utilities**: Cloud object storage clients
  - `DigitalOceanSpacesClient`: S3-compatible client for DigitalOcean Spaces
  - Simple upload and fetch operations
  - Public URL generation

- **CLI Tools**: Command-line utilities for Flask development
  - `flask_route_usage_report`: Analyze Flask routes and find their frontend usage
  - `add_usage_comments`: Add usage comment blocks above Flask route definitions
  - `remove_route_usage_comments`: Remove all usage comment blocks from Flask routes
  - Generates comprehensive markdown reports
  - Detects unused routes (dead code)
  - Supports pyproject.toml configuration

## Usage

### SQLAlchemy Mixins

```python
from sqlalchemy import Column, String
from pamfilico_python_utils import DateTimeMixin, NextAuthUserMixin, generate_uuid

class User(Base, DateTimeMixin, NextAuthUserMixin):
    __tablename__ = "users"

    # Your custom fields
    username = Column(String(50), unique=True)

    # Automatically includes:
    # - id (UUID primary key)
    # - email, name, image, phone_number
    # - password_hash
    # - created_at, updated_at (from DateTimeMixin)
```

### Flask Authentication & Error Handling

```python
from flask import Flask
from pamfilico_python_utils.flask import (
    configure_authenticatenext,
    authenticatenext,
    validate_uuid_params,
    standard_response,
    init_errors,
)
from app.database.engine import DBsession
from app.database.models.user import User
from app.database.models.staff import Staff

app = Flask(__name__)

# Configure authenticatenext ONCE during app initialization
configure_authenticatenext(
    db_session_factory=DBsession,
    masterModel=User,
    slaveModel=Staff
)

# Initialize error handlers
init_errors(app)

# Now use @authenticatenext cleanly (matches backend pattern exactly!)
@app.route('/api/customer/<customer_id>')
@validate_uuid_params
@authenticatenext
def get_customer(customer_id, auth):
    # auth dict contains: email, id, role
    return standard_response(
        data={"customer_id": customer_id, "user": auth['email']},
        ui_message="Success",
        status_code=200
    )

# With scopes
@app.route('/api/admin/dashboard')
@authenticatenext(['admin'])
def admin_dashboard(auth):
    return standard_response(data={"dashboard": "data"})
```

### Flask Pagination

```python
from flask import Flask
from pamfilico_python_utils.flask import collection, jwt_authenticator_with_scopes
from your_app.database import session
from your_app.models import Vehicle
from your_app.schemas import VehicleGetSchema

app = Flask(__name__)

# Paginated endpoint with search and sorting
@app.route('/api/vehicles')
@collection(
    VehicleGetSchema,
    searchable_fields=['name', 'license_plate', 'web_title'],
    sortable_fields=['name', 'created_at', 'license_plate']
)
@jwt_authenticator_with_scopes(['user'])
def list_vehicles(auth):
    # Return a SQLAlchemy query object (not executed)
    return session.query(Vehicle).filter_by(user_id=auth['id'])

# Usage:
# GET /api/vehicles?page_number=1&results_per_page=20
# GET /api/vehicles?search_by=name&search_value=toyota
# GET /api/vehicles?order_by=created_at&order_direction=desc
```

### DigitalOcean Spaces Storage

```python
from pamfilico_python_utils import DigitalOceanSpacesClient

# Initialize client (reads from environment variables by default)
# Required env vars: SPACES_REGION, SPACES_BUCKET, SPACES_API_KEY, SPACES_SECRET_KEY
client = DigitalOceanSpacesClient()

# Or initialize with explicit credentials
client = DigitalOceanSpacesClient(
    region='nyc3',
    bucket='my-bucket',
    api_key='your-api-key',
    secret_key='your-secret-key'
)

# Upload a file object (like from Flask request.files)
@app.route('/upload', methods=['POST'])
def upload_logo():
    logo = request.files.get('logo')
    url = client.upload_fileobj(
        file_obj=logo,
        object_name=f'users/{user_id}/logo/header_logo.png',
        content_type=logo.content_type,
        acl='public-read'
    )
    # Returns: 'https://nyc3.digitaloceanspaces.com/my-bucket/users/123/logo/header_logo.png'
    return {'url': url}

# Fetch an object
obj = client.fetch_object('users/123/logo/header_logo.png')
content = obj['Body'].read()

# Get public URL without fetching
url = client.get_public_url('users/123/logo/header_logo.png')
```

### Individual Imports

```python
# SQLAlchemy mixins
from pamfilico_python_utils.sqlalchemy import (
    DateTimeMixin,
    NextAuthUserMixin,
    NextAuthSessionMixin,
    NextAuthAccountMixin,
    NextAuthVerificationTokenMixin,
    generate_uuid,
)

# Flask utilities
from pamfilico_python_utils.flask import (
    collection,
    jwt_authenticator_with_scopes,
    validate_uuid_params,
    standard_response,
    init_errors,
)

# Storage utilities
from pamfilico_python_utils.storage import DigitalOceanSpacesClient

# CLI utilities (for programmatic use)
from pamfilico_python_utils.cli import FlaskRouteAnalyzer, RouteInfo, UsageInfo
```

### CLI Tools

#### 1. Flask Route Usage Report

Analyze Flask routes and their frontend usage to identify dead code and track API consumption:

```bash
# From your backend directory (uses pyproject.toml config)
cd backend_carfast
poetry run flask_route_usage_report

# Custom paths (overrides pyproject.toml)
poetry run flask_route_usage_report \
  --backend ./my-backend \
  --api-path app/api/v1 \
  --frontends ./frontend1 ./frontend2 \
  --frontend-src src

# View help
poetry run flask_route_usage_report --help
```

**Configuration in pyproject.toml:**

```toml
[tool.flask_route_usage]
backend = "./"
api_path = "app/api/v1"
frontends = ["../frontend_carfast_manager_web", "../frontend_rentfast_landing"]
frontend_src = "src"
```

**Output:**
- `flask_routes_with_usage.md` - Routes with frontend usage (106 routes, 148 calls)
- `flask_routes_without_usage.md` - Unused routes that may be dead code (62 routes)

**Features:**
- Extracts Flask routes from backend using regex parsing
- Scans frontend TypeScript/JavaScript files for axios/fetch API calls
- Fuzzy matching for dynamic routes (`/api/user/<user_id>`)
- Handles multi-line API calls and template variables
- Groups by HTTP method (GET, POST, PUT, DELETE, PATCH)
- Shows exact file locations with line numbers

#### 2. Add Usage Comments

Adds comment blocks above Flask route definitions showing where they're used in frontend code:

```bash
# Dry run (preview changes)
cd backend_carfast
poetry run add_usage_comments --dry-run

# Apply changes
poetry run add_usage_comments

# Custom paths (overrides pyproject.toml)
poetry run add_usage_comments \
  --backend-path ./my-backend \
  --with-usage flask_routes_with_usage.md \
  --without-usage flask_routes_without_usage.md
```

**Configuration in pyproject.toml:**

```toml
[tool.add_usage_comments]
backend_path = "./"
with_usage_report = "flask_routes_with_usage.md"
without_usage_report = "flask_routes_without_usage.md"
```

**Example output in your Flask routes:**

```python
# START: ROUTE USAGES TOOL
# ./frontend_carfast_manager_web/src/actions/insurance.ts:30
# ./frontend_carfast_manager_web/src/app/[locale]/insurance/page.tsx:48
# ./frontend_carfast_manager_web/src/app/[locale]/bookings/requests/page.tsx:189
# END: ROUTE USAGES TOOL
@api.route("/insurance", methods=["GET"])
@authenticatenext
def list_insurances(auth):
    # ...
```

**Features:**
- Places comments BEFORE decorators (correct position)
- Handles routes with no frontend usage (marks for potential deletion)
- Replaces existing comment blocks automatically
- Supports both legacy and new comment markers
- Dry-run mode for safe preview

#### 3. Remove Route Usage Comments

Removes all usage comment blocks from Flask route files:

```bash
# Remove all comment blocks
cd backend_carfast
poetry run remove_route_usage_comments

# View help
poetry run remove_route_usage_comments --help
```

**Configuration in pyproject.toml:**

```toml
[tool.remove_route_usage_comments]
backend_path = "./"
```

**Features:**
- Removes all `# START: ROUTE USAGES TOOL` / `# END: ROUTE USAGES TOOL` blocks
- Also removes legacy `# START: USAGES TOOL` / `# END: USAGES TOOL` blocks
- Safe operation (only removes known comment markers)
- Shows summary of files processed and blocks removed

#### Typical Workflow

```bash
# 1. Analyze routes and generate reports
cd backend_carfast
poetry run flask_route_usage_report

# 2. Review the generated markdown files
# - flask_routes_with_usage.md (routes being used)
# - flask_routes_without_usage.md (potential dead code)

# 3. Add comment blocks to route files (dry-run first)
poetry run add_usage_comments --dry-run
poetry run add_usage_comments

# 4. If you need to regenerate or clean up
poetry run remove_route_usage_comments
poetry run flask_route_usage_report
poetry run add_usage_comments
```

**Programmatic Usage:**

```python
from pamfilico_python_utils.cli import FlaskRouteAnalyzer

analyzer = FlaskRouteAnalyzer(
    backend_root="./backend",
    frontend_roots=["./frontend1", "./frontend2"],
    api_subpath="app/api/v1",
    frontend_src_subpath="src"
)

# Extract and analyze
analyzer.extract_routes()
analyzer.extract_frontend_usages()
analyzer.generate_split_reports()
```

## Development

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Format code
poetry run ruff format

# Lint code
poetry run ruff check
```

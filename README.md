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

- **CLI Tools**: Command-line utilities for Flask development, code refactoring, and quality analysis
  - `flask_route_usage_report`: Analyze Flask routes and find their frontend usage
  - `add_usage_comments`: Add usage comment blocks above Flask route definitions
  - `remove_route_usage_comments`: Remove all usage comment blocks from Flask routes
  - `move_imports_to_top`: Move inline imports from inside functions to the top of Python files
  - `python_quality_audit`: Comprehensive Python code quality analysis with multiple tools
  - Generates comprehensive markdown reports
  - Detects unused routes (dead code) 
  - Supports pyproject.toml configuration
  - Handles axios instance calls and complex API patterns

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
from pamfilico_python_utils.cli.move_imports_to_top import process_file, extract_inline_imports
from pamfilico_python_utils.cli.python_quality_audit import generate_report, check_tools
```

### CLI Tools

#### 1. Flask Route Usage Report

Analyze Flask routes and their frontend usage to identify dead code and track API consumption:

```bash
# From your backend directory (uses pyproject.toml config if available)
cd your-backend-directory
poetry run flask_route_usage_report

# Backend routes only (no frontend analysis)
poetry run flask_route_usage_report

# With frontend analysis
poetry run flask_route_usage_report --frontends ../your-frontend

# Custom paths (overrides pyproject.toml)
poetry run flask_route_usage_report \
  --backend ./ \
  --api-path app \
  --frontends ../frontend1 ../frontend2 \
  --frontend-src src

# View help
poetry run flask_route_usage_report --help
```

**Configuration in your backend's pyproject.toml:**

```toml
[tool.flask_route_usage]
backend = "./"
api_path = "app"
frontends = ["../your-frontend1", "../your-frontend2"]
frontend_src = "src"
```

You can add this configuration to your backend project's pyproject.toml to avoid having to specify paths every time.

**Output:**
- `flask_routes_with_usage.md` - Routes with frontend usage (106 routes, 148 calls)
- `flask_routes_without_usage.md` - Unused routes that may be dead code (62 routes)

**Features:**
- Extracts Flask routes from backend using regex parsing
- Scans frontend TypeScript/JavaScript files for axios/fetch API calls
- Detects both direct axios calls (`axios.get()`) and instance calls (`apiClient.get()`)
- Handles baseURL prefixes and API client configurations
- Fuzzy matching for dynamic routes (`/api/user/<user_id>`)
- Handles multi-line API calls and template variables
- Groups by HTTP method (GET, POST, PUT, DELETE, PATCH)
- Shows exact file locations with line numbers
- Supports verbose debugging output for troubleshooting

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

#### 4. Move Imports to Top

# This tool was created because of Claude's bullshit habit of putting imports inside functions

Extracts all inline imports from inside functions and moves them to the top of Python files. This is particularly useful for Flask route files that have imports scattered throughout functions:

```bash
# Dry run (preview changes) on current directory
poetry run move_imports_to_top --dry-run

# Process specific directory with pattern
poetry run move_imports_to_top --backend-path ./backend --pattern "app/api/v1/*.py" --dry-run

# Live mode (actually modify files)
poetry run move_imports_to_top --pattern "app/api/v1/*.py"

# Process all Python files in backend
poetry run move_imports_to_top --backend-path ./backend

# View help
poetry run move_imports_to_top --help
```

**Configuration in pyproject.toml:**

```toml
[tool.move_imports_to_top]
backend_path = "./backend"
```

**Example transformation:**

Before:
```python
@app.route('/api/users', methods=['GET'])
def list_users():
    from app.services.user_service import UserService
    from app.database.models import User
    import json
    
    users = UserService.get_all()
    return json.dumps(users)

@app.route('/api/posts', methods=['GET']) 
def list_posts():
    from app.services.post_service import PostService
    from datetime import datetime
    
    posts = PostService.get_recent()
    return posts
```

After:
```python
from app.services.user_service import UserService
from app.database.models import User
import json
from app.services.post_service import PostService
from datetime import datetime

@app.route('/api/users', methods=['GET'])
def list_users():
    users = UserService.get_all()
    return json.dumps(users)

@app.route('/api/posts', methods=['GET']) 
def list_posts():
    posts = PostService.get_recent()
    return posts
```

**Features:**
- Detects imports with indentation (inside functions/classes)
- Preserves existing top-level imports and adds new ones after them
- Handles docstrings and comments correctly
- Supports glob patterns for file selection (e.g., `"app/api/v1/*.py"`)
- Removes duplicate imports automatically
- Dry-run mode for safe preview
- Shows detailed progress and debugging output
- Configurable backend directory path
- Skips files with no inline imports

**Command Line Options:**
- `--dry-run`: Preview changes without modifying files
- `--backend-path <path>`: Path to backend directory (default: `./`)
- `--pattern <pattern>`: File pattern to match (default: `**/*.py`)

**Use Cases:**
- Cleaning up Flask route files with scattered imports
- Refactoring legacy code with poor import organization
- Preparing code for linting tools that require imports at the top
- Standardizing import patterns across a codebase

#### 5. Python Quality Audit

Runs comprehensive Python code quality analysis using multiple industry-standard tools and generates detailed markdown reports. Reports are saved in `audit/` directories next to the analyzed files.

```bash
# Analyze single file - saves to audit/filename.md
poetry run python_quality_audit src/app.py

# Analyze with strict complexity threshold
poetry run python_quality_audit src/app.py --complexity A

# Analyze multiple files with pattern
poetry run python_quality_audit --pattern "src/**/*.py"

# Preview what files would be analyzed
poetry run python_quality_audit --pattern "src/**/*.py" --dry-run

# View help
poetry run python_quality_audit --help
```

**Configuration in pyproject.toml:**

```toml
[tool.python_quality_audit]
complexity = "A"  # A=strict, B=good, C=fair (default), D=poor, E=bad, F=worst
pattern = "src/**/*.py"
```

**Analysis Tools Included:**

1. **Radon** - Cyclomatic complexity, Maintainability Index, Halstead metrics
2. **Xenon** - Complexity threshold checking (fails if code exceeds limits)
3. **Cohesion** - LCOM (Lack of Cohesion of Methods) for class analysis
4. **Bandit** - Security vulnerability detection
5. **Pylint** - Code quality, style, and error analysis
6. **Vulture** - Dead code detection (unused functions, variables, imports)

**Report Structure:**
- Cyclomatic Complexity (McCabe) - Code path complexity grading A-F
- Complexity Thresholds - Pass/fail based on configurable limits
- Maintainability Index - Overall maintainability scoring
- Halstead Metrics - Software science metrics for code understanding
- Class Cohesion - How well-structured your classes are
- Security Issues - Potential vulnerabilities and bad practices  
- Code Quality - Style issues, errors, and refactoring suggestions
- Dead Code - Unused code that can be safely removed

**Features:**
- Auto-creates `audit/` directories next to analyzed files
- Supports single file or bulk analysis with glob patterns
- Configurable complexity thresholds and tool options
- Comprehensive markdown reports with academic references
- Dry-run mode to preview analysis targets
- Progress reporting for multiple file analysis
- Missing tool detection with installation guidance

**Example Report Location:**
```
src/
├── app.py
├── models.py
└── audit/
    ├── app.md      # Quality report for app.py
    └── models.md   # Quality report for models.py
```

**Use Cases:**
- Pre-commit quality checks and code review preparation
- Technical debt assessment and refactoring planning
- Security audit and vulnerability assessment
- Code complexity monitoring and maintainability tracking
- Dead code cleanup and codebase optimization
- Academic research requiring quantitative code metrics

#### Typical Workflow

```bash
# 1. Clean up imports in your route files (optional but recommended first)
cd your-backend-directory
poetry run move_imports_to_top --pattern "app/api/v1/*.py" --dry-run
poetry run move_imports_to_top --pattern "app/api/v1/*.py"

# 2. Run quality audit on your codebase (starts with fair threshold C)
poetry run python_quality_audit --pattern "src/**/*.py" --dry-run
poetry run python_quality_audit --pattern "src/**/*.py"

# 2a. For stricter analysis, use --complexity A or B
poetry run python_quality_audit --pattern "src/**/*.py" --complexity B

# 3. Analyze routes and generate reports
poetry run flask_route_usage_report

# 4. Review the generated files
# - audit/*.md (quality reports for each file)
# - flask_routes_with_usage.md (routes being used)
# - flask_routes_without_usage.md (potential dead code)

# 5. Add comment blocks to route files (dry-run first)
poetry run add_usage_comments --dry-run
poetry run add_usage_comments

# 6. If you need to regenerate or clean up
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

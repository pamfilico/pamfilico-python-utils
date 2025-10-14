# Pamfilico Python Utils

Python utility functions and helpers for common tasks.

## Installation

Install directly from GitHub using Poetry:

```bash
poetry add git+https://github.com/yourusername/pamfilico-python-utils.git
```

Or with pip:

```bash
pip install git+https://github.com/yourusername/pamfilico-python-utils.git
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
  - `standard_response`: Consistent API response formatting
  - Custom error classes and Flask error handlers
  - JWE token encryption/decryption utilities

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
    jwt_authenticator_with_scopes,
    validate_uuid_params,
    admin_required,
    standard_response,
    init_errors,
    AuthenticationError,
    NotFoundError,
)

app = Flask(__name__)

# Initialize error handlers
init_errors(app)

# Protected endpoint with JWT authentication
@app.route('/api/protected')
@jwt_authenticator_with_scopes(['user'])
def protected_endpoint(auth):
    # auth dict contains: email, id, role
    return standard_response(
        data={"message": f"Hello {auth['email']}"},
        ui_message="Success",
        status_code=200
    )

# UUID validation
@app.route('/api/item/<item_id>')
@validate_uuid_params
def get_item(item_id):
    # item_id is validated as UUID
    return standard_response(data={"item_id": item_id})

# Admin-only endpoint
@app.route('/api/admin/dashboard')
@admin_required()
def admin_dashboard():
    return standard_response(data={"dashboard": "data"})
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
    jwt_authenticator_with_scopes,
    validate_uuid_params,
    standard_response,
    init_errors,
)
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

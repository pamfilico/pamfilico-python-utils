"""
Authentication and validation decorators for Flask APIs.

This module provides decorators for authentication, authorization, and parameter validation.

Components
----------
jwt_authenticator_with_scopes
    Decorator for authenticating and authorizing API endpoints using JWT tokens
validate_uuid_params
    Decorator for validating UUID parameters in request paths
encode_jwe/decode_jwe
    Utilities for handling JWE (JSON Web Encryption) token encryption/decryption

Features
--------
- JWT authentication with role-based access control
- UUID parameter validation
- Token encryption and decryption using JWE

Examples
--------
Using the JWT authenticator:

>>> @jwt_authenticator_with_scopes(['user'])
... def protected_endpoint():
...     # Only authenticated users can access this endpoint
...     pass

Validating UUID parameters:

>>> @validate_uuid_params
... def get_item(item_id):
...     # item_id is guaranteed to be a valid UUID
...     pass

Notes
-----
The module requires certain environment variables to be set:
    - NEXTAUTH_SECRET: Secret key used for JWT encryption/decryption
"""

import json
import logging
import os
import uuid
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

from dotenv import load_dotenv
from flask import request
from hkdf import Hkdf
from jose.jwe import decrypt, encrypt

from pamfilico_python_utils.flask.errors import (
    AuthenticationError,
    EnvironmentVariableError,
    NotFoundError,
    ServerError,
)
from pamfilico_python_utils.flask.responses import standard_response


logger = logging.getLogger(__name__)


load_dotenv(override=True)

NEXTAUTH_SECRET = os.getenv("NEXTAUTH_SECRET")
TOKEN_NAME = os.getenv("TOKEN_NAME", "CARFAST_TOKEN")


def __encryption_key(secret: str):
    """Generate an encryption key from a secret using HKDF.

    Parameters
    ----------
    secret : str
        The secret from which to derive the encryption key

    Returns
    -------
    bytes
        The generated encryption key
    """
    return Hkdf("", bytes(secret, "utf-8")).expand(
        b"NextAuth.js Generated Encryption Key", 32
    )


# TODO: fc9a6086-bc7e-46a8-92a1-53aec141f41b - Add expiration
def encode_jwe(payload: Dict[str, Any], secret: str):
    """Encode a payload into a JWE token.

    Parameters
    ----------
    payload : Dict[str, Any]
        The data to encode
    secret : str
        The secret used for encryption

    Returns
    -------
    str
        The encoded JWE token
    """
    if secret is None:
        raise EnvironmentVariableError("Missing NEXTAUTH_SECRET")
    data = bytes(json.dumps(payload), "utf-8")
    key = __encryption_key(secret)
    return bytes.decode(encrypt(data, key), "utf-8")


def decode_jwe_token(token: str, secret: str, roles: Optional[List[str]] = None):
    """Decode and verify a JWE token.

    Parameters
    ----------
    token : str
        The JWE token to decode
    secret : str
        The secret key for decryption
    roles : Optional[List[str]], optional
        List of valid roles, by default None

    Returns
    -------
    Dict[str, Any]
        Dictionary containing verification status, error message, email, and role
    """
    roles = roles or ["user", ""]
    token_decrypted = decrypt(token, __encryption_key(secret))
    if token_decrypted is None:
        return {"verified": False, "error": "Invalid token", "email": "", "role": ""}
    token_decrypted_decoded = json.loads(bytes.decode(token_decrypted, "utf-8"))
    role = token_decrypted_decoded.get("role", "")
    if role not in roles:
        logger.error(
            "Invalid role: %s %s", role, json.dumps(token_decrypted_decoded, indent=2)
        )
        return {"verified": False, "error": "Invalid role", "email": "", "role": ""}
    if token_decrypted:
        if role == "user":
            user_payload_serialized = {
                "verified": True,
                "error": None,
                "email": token_decrypted_decoded.get("email", ""),
                "role": token_decrypted_decoded.get("role", ""),
                "id": token_decrypted_decoded.get("id", ""),
            }
            return user_payload_serialized

        if role == "staff":
            user_payload_serialized = {
                "verified": True,
                "error": None,
                "role": token_decrypted_decoded.get("role", ""),
                "id": token_decrypted_decoded.get("id", ""),
            }
            return user_payload_serialized
    return {"verified": False, "error": "Invalid token", "email": "", "role": ""}


def jwt_authenticator_with_scopes(
    scopes: Union[None, List[str], Callable[..., Any]] = None,
    db_session_factory: Optional[Callable] = None,
    user_model: Optional[Any] = None,
    staff_model: Optional[Any] = None,
):
    """Authenticate and authorize users based on JWT tokens and scopes.

    Parameters
    ----------
    scopes : Union[None, List[str], Callable], optional
        Required scopes for access, by default None
    db_session_factory : Optional[Callable], optional
        Function that returns a database session, by default None
    user_model : Optional[Any], optional
        User model class for database queries, by default None
    staff_model : Optional[Any], optional
        Staff model class for database queries, by default None

    Returns
    -------
    Callable
        Decorated function that checks authentication and authorization

    Raises
    ------
    AuthenticationError
        If no token is provided or user is not found
    ServerError
        If NEXTAUTH_SECRET is missing

    Notes
    -----
    If db_session_factory, user_model, or staff_model are not provided,
    the decorator will only validate the token but not perform database lookups.
    """

    if callable(scopes):
        # Called without parentheses
        return jwt_authenticator_with_scopes()(scopes)

    scopes = scopes or ["user", ""]
    default_scopes = ["admin", ""]

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.headers.get(TOKEN_NAME, None)
            if token is None:
                raise AuthenticationError("No token provided")
            if NEXTAUTH_SECRET is None:
                raise ServerError("NEXTAUTH_SECRET is missing.")
            token_decoded = decode_jwe_token(
                token, NEXTAUTH_SECRET, roles=["user", "admin", "staff", "client", ""]
            )

            role = token_decoded["role"]
            user_email = token_decoded.get("email")
            human_id = token_decoded["id"]

            if not token_decoded["verified"]:
                logger.warning("Invalid token: %s", token_decoded["error"])
                return standard_response(
                    data=None,
                    error=True,
                    ui_message="Check your token",
                    status_code=401,
                )

            if role not in scopes + default_scopes:
                return standard_response(
                    data=None,
                    error=True,
                    ui_message="Insufficient permissions",
                    status_code=403,
                )

            # If database models are provided, perform database lookups
            if db_session_factory and user_model:
                session = db_session_factory()
                try:
                    if (role == "user") | (role == ""):
                        user = (
                            session.query(user_model).filter_by(email=user_email).first()
                        )
                        if not user:
                            raise AuthenticationError(
                                f"User not found with email: {user_email}", session
                            )
                        kwargs["auth"] = {
                            "email": user_email,
                            "id": user.id,
                            "role": "user",
                        }

                    if role == "staff" and staff_model:
                        staff = (
                            session.query(staff_model).filter(staff_model.id == str(human_id)).first()
                        )
                        if not staff:
                            raise AuthenticationError(
                                f"staff not found with id: {human_id}", session
                            )
                        user = session.query(user_model).get(staff.user_id)
                        if not user:
                            raise AuthenticationError(
                                f"User not found with email: {user_email}", session
                            )
                        kwargs["auth"] = {
                            "email": user_email,
                            "id": user.id,
                            "user_id": user.id,
                            "staff_id": staff.id,
                            "role": "staff",
                        }
                finally:
                    session.close()
            else:
                # No database lookup - just pass token data
                kwargs["auth"] = {
                    "email": user_email,
                    "id": human_id,
                    "role": role,
                }

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def validate_uuid_params(func):
    """Validate that parameters ending with '_id' are valid UUIDs.

    Parameters
    ----------
    func : Callable
        The function to be decorated

    Returns
    -------
    Callable
        Decorated function that validates UUID parameters

    Raises
    ------
    NotFoundError
        If any ID parameter is not a valid UUID
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        for param, value in kwargs.items():
            if param.endswith("_id"):
                try:
                    uuid.UUID(value, version=4)
                except ValueError as exc:
                    raise NotFoundError(f"Invalid UUID: {value}.") from exc

        return func(*args, **kwargs)

    return wrapper


def admin_required(admin_token_manager: Optional[Any] = None):
    """Decorator to require valid admin token for endpoint access.

    Parameters
    ----------
    admin_token_manager : Optional[Any], optional
        Admin token manager with validate_token method, by default None

    Returns
    -------
    Callable
        Decorator function
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get token from Authorization header or ADMIN-TOKEN header
            auth_header = request.headers.get("Authorization")
            admin_token_header = request.headers.get("ADMIN-TOKEN")

            token = None

            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            elif admin_token_header:
                token = admin_token_header

            if not token:
                response, status_code = standard_response(
                    error=True,
                    message="Admin authentication required",
                    ui_message="Access denied. Admin login required.",
                    status_code=401,
                )
                return response, status_code

            # Validate token if admin_token_manager is provided
            if admin_token_manager:
                token_data = admin_token_manager.validate_token(token)
                if not token_data:
                    response, status_code = standard_response(
                        error=True,
                        message="Invalid or expired admin token",
                        ui_message="Session expired. Please login again.",
                        status_code=401,
                    )
                    return response, status_code

            return f(*args, **kwargs)

        return decorated_function

    return decorator

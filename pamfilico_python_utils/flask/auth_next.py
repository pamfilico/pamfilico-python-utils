"""
NextAuth-specific authentication decorators for Flask APIs.

This module provides NextAuth.js-compatible JWT authentication with database lookups.
"""

import logging
import os
from functools import wraps
from typing import Any, Callable, List, Optional, Union

from dotenv import load_dotenv
from flask import request

from pamfilico_python_utils.flask.auth import decode_jwe_token
from pamfilico_python_utils.flask.errors import AuthenticationError, ServerError
from pamfilico_python_utils.flask.responses import standard_response


logger = logging.getLogger(__name__)
load_dotenv(override=True)

NEXTAUTH_SECRET = os.getenv("NEXTAUTH_SECRET")
TOKEN_NAME = os.getenv("TOKEN_NAME", "CARFAST_TOKEN")


# Module-level configuration
_db_session_factory: Optional[Callable] = None
_master_model: Optional[Any] = None
_slave_model: Optional[Any] = None


def configure_authenticatenext(
    db_session_factory: Callable,
    masterModel: Any,
    slaveModel: Optional[Any] = None,
):
    """
    Configure the authenticatenext decorator with database session and models.

    This function must be called once during application initialization before
    using the @authenticatenext decorator.

    Parameters
    ----------
    db_session_factory : Callable
        Function that returns a database session (e.g., DBsession)
    masterModel : Any
        Master model class for database queries (e.g., User model)
    slaveModel : Any, optional
        Slave model class for database queries (e.g., Staff model)

    Examples
    --------
    Configure once during app initialization:

    >>> from pamfilico_python_utils.flask import configure_authenticatenext
    >>> from app.database.engine import DBsession
    >>> from app.database.models.user import User
    >>> from app.database.models.staff import Staff
    >>>
    >>> configure_authenticatenext(
    ...     db_session_factory=DBsession,
    ...     masterModel=User,
    ...     slaveModel=Staff
    ... )

    Then use the decorator without parameters in your routes:

    >>> @app.route('/api/protected')
    >>> @authenticatenext
    >>> def protected_endpoint(auth):
    ...     return {'user_id': auth['id']}
    """
    global _db_session_factory, _master_model, _slave_model
    _db_session_factory = db_session_factory
    _master_model = masterModel
    _slave_model = slaveModel
    logger.info("authenticatenext configured with masterModel=%s, slaveModel=%s",
                masterModel.__name__ if masterModel else None,
                slaveModel.__name__ if slaveModel else None)


def authenticatenext(
    scopes: Union[None, List[str], Callable[..., Any]] = None,
):
    """
    Authenticate and authorize users based on JWT tokens and scopes.

    This decorator requires configuration via configure_authenticatenext() before use.
    Once configured, use it exactly like the backend: @authenticatenext

    Parameters
    ----------
    scopes : Union[None, List[str], Callable], optional
        Required scopes for access, by default None

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
    RuntimeError
        If configure_authenticatenext() has not been called

    Examples
    --------
    Configure once during app initialization:

    >>> from pamfilico_python_utils.flask import configure_authenticatenext, authenticatenext
    >>> from app.database.engine import DBsession
    >>> from app.database.models.user import User, Staff
    >>>
    >>> configure_authenticatenext(DBsession, User, Staff)

    Then use cleanly in routes (matches backend pattern):

    >>> @app.route('/api/customer')
    >>> @authenticatenext
    >>> def get_customer(auth):
    ...     return {'user_id': auth['id']}
    >>>
    >>> @app.route('/api/admin')
    >>> @authenticatenext(['admin'])
    >>> def admin_only(auth):
    ...     return {'admin': True}
    """

    if callable(scopes):
        # Called without parentheses: @authenticatenext
        return authenticatenext()(scopes)

    # Check if configured
    if _db_session_factory is None or _master_model is None:
        raise RuntimeError(
            "authenticatenext has not been configured. "
            "Call configure_authenticatenext(db_session_factory, masterModel, slaveModel) "
            "during application initialization."
        )

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

            session = _db_session_factory()
            try:
                if (role == "user") | (role == ""):
                    master = (
                        session.query(_master_model).filter_by(email=user_email).first()
                    )
                    if not master:
                        raise AuthenticationError(
                            f"User not found with email: {user_email}", session
                        )
                    kwargs["auth"] = {
                        "email": user_email,
                        "id": master.id,
                        "role": "user",
                    }

                if role == "staff" and _slave_model:
                    slave = (
                        session.query(_slave_model).filter(_slave_model.id == str(human_id)).first()
                    )
                    if not slave:
                        raise AuthenticationError(
                            f"staff not found with id: {human_id}", session
                        )
                    master = session.query(_master_model).get(slave.user_id)
                    if not master:
                        raise AuthenticationError(
                            f"User not found with email: {user_email}", session
                        )
                    kwargs["auth"] = {
                        "email": user_email,
                        "id": master.id,
                        "user_id": master.id,
                        "staff_id": slave.id,
                        "role": "staff",
                    }
            finally:
                session.close()

            return f(*args, **kwargs)

        return decorated_function

    return decorator

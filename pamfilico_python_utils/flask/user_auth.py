"""
NextAuth REST-style auth blueprint for Flask.

Registers a configurable blueprint with NextAuth adapter endpoints (users, sessions,
accounts, verification tokens). Use for testing without modifying existing api/v1 auth.

All responses use standard_response. Does not depend on flask/auth or auth_next.
"""

import uuid
from typing import Any, Callable, Optional

from dateutil import parser
from flask import Flask, request

from pamfilico_python_utils.flask.errors import DatabaseError, NotFoundError
from pamfilico_python_utils.flask.responses import standard_response


def _safe_iso(value) -> Optional[str]:
    """Format datetime for JSON; return None if None."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _parse_user_id(value: Any) -> Any:
    """Parse user_id from URL or JSON; support UUID string."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return value


def _user_to_dict(user: Any) -> dict:
    """Serialize user to NextAuth shape."""
    return {
        "id": str(user.id) if user.id else None,
        "email": getattr(user, "email", None),
        "emailVerified": _safe_iso(getattr(user, "emailVerified", None)),
        "name": getattr(user, "name", None),
        "image": getattr(user, "image", None),
    }


def init_user_auth(
    app: Flask,
    db_session_factory: Callable,
    user_model: Any,
    session_model: Any,
    account_model: Any,
    verification_token_model: Any,
    url_prefix: str = "/api/v2/auth",
) -> None:
    """Register NextAuth REST-style auth blueprint with configurable URL prefix.

    Call once during app initialization. Registers routes under the given prefix.
    Use a different prefix (e.g. /api/v2/auth) to test without touching api/v1.

    Parameters
    ----------
    app : Flask
        Flask application instance
    db_session_factory : Callable
        Function returning a database session (e.g. DBsession)
    user_model : type
        User model class (e.g. User)
    session_model : type
        Session model class (e.g. UserSession)
    account_model : type
        Account model class (e.g. UserAccount)
    verification_token_model : type
        VerificationToken model class (e.g. UserVerificationToken)
    url_prefix : str, optional
        Blueprint URL prefix. Defaults to /api/v2/auth.

    Examples
    --------
    >>> from flask import Flask
    >>> from pamfilico_python_utils.flask.user_auth import init_user_auth
    >>> from app.database.engine import DBsession
    >>> from app.database.models.user import User, UserSession, UserAccount, UserVerificationToken
    >>>
    >>> app = Flask(__name__)
    >>> init_user_auth(app, DBsession, User, UserSession, UserAccount, UserVerificationToken,
    ...               url_prefix="/api/v2/auth")
    """
    from flask import Blueprint

    bp = Blueprint("user_auth", __name__, url_prefix=url_prefix)

    @bp.route("/users", methods=["POST"])
    def create_user():
        data = request.get_json() or {}
        email = data.get("email")
        name = data.get("name", "Your Name")
        image = data.get("image")

        if not email:
            return standard_response(
                error=True,
                ui_message="Email is required",
                status_code=400,
            )

        session = db_session_factory()
        try:
            existing = session.query(user_model).filter_by(email=email).first()
            if existing:
                existing.name = name
                existing.image = image
                if hasattr(existing, "emailVerified") and not existing.emailVerified:
                    pass
                session.commit()
                user = existing
            else:
                username = email.split("@")[0] if "@" in email else email
                kwargs = {"email": email, "name": name, "image": image}
                if hasattr(user_model, "username"):
                    kwargs["username"] = username
                user = user_model(**kwargs)
                session.add(user)
                session.commit()
            response_data = _user_to_dict(user)
            return standard_response(data=response_data, status_code=200)
        except Exception as e:
            raise DatabaseError(f"Failed to create user: {str(e)}", session=session)
        finally:
            session.close()

    @bp.route("/users/<user_id>", methods=["PUT"])
    def update_user(user_id):
        data = request.get_json() or {}
        uid = _parse_user_id(user_id)
        session = db_session_factory()
        try:
            user = session.query(user_model).filter(user_model.id == uid).first()
            if not user:
                raise NotFoundError(f"No user with id {user_id}", session=session)
            if "email" in data and data["email"] is not None:
                user.email = data["email"]
            if "name" in data:
                user.name = data["name"]
            if "image" in data:
                user.image = data["image"]
            session.commit()
            return standard_response(data=_user_to_dict(user), status_code=200)
        except (NotFoundError, DatabaseError):
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to update user: {str(e)}", session=session)
        finally:
            session.close()

    @bp.route("/users/<user_id>", methods=["GET"])
    def get_user_by_id(user_id):
        uid = _parse_user_id(user_id)
        session = db_session_factory()
        try:
            user = session.query(user_model).filter(user_model.id == uid).first()
            if not user:
                return standard_response(
                    error=True,
                    ui_message="User not found",
                    status_code=404,
                )
            return standard_response(data=_user_to_dict(user), status_code=200)
        finally:
            session.close()

    @bp.route("/users/email/<path:email>", methods=["GET"])
    def get_user_by_email(email):
        session = db_session_factory()
        try:
            user = session.query(user_model).filter_by(email=email).first()
            if not user:
                return standard_response(
                    error=True,
                    ui_message="User not found",
                    status_code=404,
                )
            return standard_response(data=_user_to_dict(user), status_code=200)
        finally:
            session.close()

    def _account_provider_id_attr():
        if hasattr(account_model, "providerAccountId"):
            return "providerAccountId"
        return "provider_account_id"

    def _account_user_id_attr():
        if hasattr(account_model, "userId"):
            return "userId"
        return "user_id"

    @bp.route("/accounts", methods=["POST"])
    def create_account():
        data = request.get_json() or {}
        user_id_attr = _account_user_id_attr()
        provider_id_attr = _account_provider_id_attr()

        user_id = data.get("userId") or data.get("user_id")
        provider_account_id = data.get("providerAccountId") or data.get(
            "provider_account_id"
        )
        type_val = data.get("type")
        provider = data.get("provider")

        if not all([user_id, provider_account_id, type_val, provider]):
            return standard_response(
                error=True,
                ui_message="userId, providerAccountId, type, provider required",
                status_code=400,
            )

        session = db_session_factory()
        try:
            kwargs = {
                user_id_attr: user_id,
                provider_id_attr: provider_account_id,
                "type": type_val,
                "provider": provider,
                "refresh_token": data.get("refresh_token"),
                "access_token": data.get("access_token"),
                "expires_at": data.get("expires_at"),
                "id_token": data.get("id_token"),
                "scope": data.get("scope"),
                "session_state": data.get("session_state"),
                "token_type": data.get("token_type"),
            }
            kwargs = {k: v for k, v in kwargs.items() if v is not None}
            account = account_model(**kwargs)
            session.add(account)
            session.commit()
            response_data = {
                "id": str(account.id),
                "userId": getattr(account, user_id_attr, user_id),
                "providerAccountId": getattr(account, provider_id_attr, provider_account_id),
                "type": account.type,
                "provider": account.provider,
            }
            return standard_response(data=response_data, status_code=200)
        except Exception as e:
            raise DatabaseError(f"Failed to create account: {str(e)}", session=session)
        finally:
            session.close()

    @bp.route("/sessions", methods=["POST"])
    def create_session():
        data = request.get_json() or {}
        user_id = data.get("userId") or data.get("user_id")
        session_token = data.get("sessionToken")
        expires_str = data.get("expires")

        if not all([user_id, session_token, expires_str]):
            return standard_response(
                error=True,
                ui_message="userId, sessionToken, expires required",
                status_code=400,
            )

        try:
            expires_dt = parser.isoparse(expires_str)
        except (ValueError, TypeError):
            return standard_response(
                error=True,
                ui_message="Invalid date format for expires",
                status_code=400,
            )

        session = db_session_factory()
        try:
            new_session = session_model(
                user_id=user_id,
                expires=expires_dt,
                sessionToken=session_token,
            )
            session.add(new_session)
            session.commit()

            user = session.query(user_model).filter(user_model.id == user_id).first()
            if user:
                response_data = {
                    "id": str(new_session.user_id),
                    "email": user.email,
                    "name": user.name,
                    "role": "user",
                }
            else:
                response_data = {
                    "id": str(new_session.user_id),
                    "sessionToken": new_session.sessionToken,
                    "expires": new_session.expires.strftime(
                        "%Y-%m-%dT%H:%M:%S.%f"
                    )[:-3]
                    + "Z",
                }
            return standard_response(data=response_data, status_code=200)
        except Exception as e:
            raise DatabaseError(f"Failed to create session: {str(e)}", session=session)
        finally:
            session.close()

    @bp.route("/verification_tokens", methods=["POST"])
    def create_verification_token():
        data = request.get_json() or {}
        identifier = data.get("identifier")
        token = data.get("token")
        expires_str = data.get("expires")

        if not all([identifier, token, expires_str]):
            return standard_response(
                error=True,
                ui_message="identifier, token, expires required",
                status_code=400,
            )

        try:
            expires_dt = parser.isoparse(expires_str)
        except (ValueError, TypeError):
            return standard_response(
                error=True,
                ui_message="Invalid date format for expires",
                status_code=400,
            )

        session = db_session_factory()
        try:
            vt = verification_token_model(
                identifier=identifier, expires=expires_dt, token=token
            )
            session.add(vt)
            session.commit()
            response_data = {
                "identifier": vt.identifier,
                "expires": vt.expires.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "token": vt.token,
            }
            return standard_response(data=response_data, status_code=200)
        except Exception as e:
            raise DatabaseError(
                f"Failed to create verification token: {str(e)}", session=session
            )
        finally:
            session.close()

    @bp.route("/verification_tokens/use", methods=["GET"])
    def use_verification_token():
        token = request.args.get("token")
        identifier = request.args.get("identifier")

        if not token or not identifier:
            return standard_response(
                error=True,
                ui_message="token and identifier query params required",
                status_code=400,
            )

        session = db_session_factory()
        try:
            vt = (
                session.query(verification_token_model)
                .filter(
                    verification_token_model.token == token,
                    verification_token_model.identifier == identifier,
                )
                .first()
            )
            if not vt:
                return standard_response(
                    error=True,
                    ui_message="Invalid token",
                    status_code=400,
                )
            session.delete(vt)
            session.commit()
            response_data = {
                "identifier": vt.identifier,
                "expires": _safe_iso(vt.expires),
                "token": vt.token,
            }
            return standard_response(data=response_data, status_code=200)
        except Exception as e:
            raise DatabaseError(
                f"Failed to use verification token: {str(e)}", session=session
            )
        finally:
            session.close()

    app.register_blueprint(bp)

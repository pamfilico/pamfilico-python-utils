import logging
import traceback

from marshmallow.exceptions import ValidationError
from sqlalchemy.exc import DataError, IntegrityError, OperationalError
from werkzeug.exceptions import HTTPException

from pamfilico_python_utils.flask.responses import standard_response

logger = logging.getLogger(__name__)

DEBUG = True  # global variable setting the debug config


class BaseError(Exception):
    """Base exception for all custom Flask API errors.

    Automatically rolls back and closes the database session when provided,
    preventing orphaned transactions. All other error classes inherit from this.

    Args:
        message: Human-readable error description.
        session: Optional SQLAlchemy session to roll back on error.

    Examples:
        >>> raise BaseError("Something went wrong")
        >>> raise NotFoundError("User not found", session=session)
    """

    def __init__(self, message, session=None):
        self.session = session
        super().__init__(message)
        if self.session:
            try:
                logger.error("RollingBack session")
                self.session.rollback()
                self.session.close()
            except Exception as e:  # pylint: disable=broad-except
                logger.error("Error rolling back session: %s", e)
                traceback_info = traceback.format_exc()
                logger.error("Traceback: %s", traceback_info)


class BizlogicError(BaseError):
    """Business logic rule violation (e.g. invalid state transition).

    Mapped to 400 Bad Request by default if registered. Use for domain
    rule violations that don't fit NotFound, AlreadyExists, or auth errors.

    Examples:
        >>> raise BizlogicError("Cannot delete vehicle with active bookings")
        >>> raise BizlogicError("Subscription expired", session=session)
    """

    pass


class DataNotFoundError(BaseError):
    """Entity not found when querying by ID or other lookup.

    Returns 404. Use for repository/service layer "get by id" failures
    (e.g. subscription, notification, feedback not found).

    Examples:
        >>> raise DataNotFoundError(f"Feedback with id {feedback_id} not found")
        >>> raise DataNotFoundError("Push subscription not found", session=session)
    """

    pass


class VehicleError(BaseError):
    """Vehicle domain or operation constraint violation.

    Returns 400. Use for vehicle-specific rules (e.g. cannot delete,
    cannot update, conflicting bookings).

    Examples:
        >>> raise VehicleError("Delete bookings first", session=session)
        >>> raise VehicleError("Vehicle is currently booked")
    """

    pass


class AlreadyExistsError(BaseError):
    """Duplicate resource (unique constraint or logical duplicate).

    Returns 409 Conflict. Use when creating/updating would violate
    uniqueness (e.g. same name, license plate, email).

    Examples:
        >>> raise AlreadyExistsError("Location with name 'Warehouse A' already exists")
        >>> raise AlreadyExistsError("Booking for this vehicle already exists", session=session)
    """

    pass


class NotFoundError(BaseError):
    """Resource not found (generic 404).

    Returns 404. Use for API-level "not found" (user, vehicle, config, etc.)
    when the resource does not exist or the user lacks access.

    Examples:
        >>> raise NotFoundError("Vehicle not found", session=session)
        >>> raise NotFoundError(f"User with id {user_id} not found")
    """

    pass


class ServerError(BaseError):
    """Internal server or dependency failure.

    Returns 500. Use for unexpected backend failures (external API down,
    config missing, etc.) when you want explicit 500 handling.

    Examples:
        >>> raise ServerError("Payment provider unavailable")
        >>> raise ServerError("Failed to send email", session=session)
    """

    pass


class DatabaseError(BaseError):
    """Database constraint or integrity violation (wrapped).

    Returns 409. Use when you catch SQLAlchemy errors and re-raise
    with a user-friendly message (e.g. unique, FK violation).

    Examples:
        >>> raise DatabaseError("Object already exists.", session=session)
        >>> raise DatabaseError("Referenced record does not exist")
    """

    pass


class AuthenticationError(BaseError):
    """Invalid or missing authentication (token, user not found).

    Returns 401. Raised by auth decorators when token is invalid/expired
    or the user does not exist in the database.

    Examples:
        >>> raise AuthenticationError("Invalid token")
        >>> raise AuthenticationError("User not found")
    """

    pass


class EnvironmentVariableError(BaseError):
    """Required environment variable missing or invalid.

    Typically raised at app startup (e.g. NEXTAUTH_SECRET, SQLALCHEMY_DATABASE_URI).
    Not registered in init_errors—usually allowed to crash the app.

    Examples:
        >>> raise EnvironmentVariableError("NEXTAUTH_SECRET not set")
        >>> raise EnvironmentVariableError("SQLALCHEMY_DATABASE_URI not defined")
    """

    pass


class StripeError(BaseError):
    """Stripe API or payment processing failure.

    Returns 404 (per Travelsuite pattern). Use when Stripe calls fail
    (card declined, customer not found, etc.).

    Examples:
        >>> raise StripeError("Payment method not found")
        >>> raise StripeError("Customer has no default payment method", session=session)
    """

    pass


class ForbidenError(BaseError):
    """Forbidden access (user authenticated but not authorized).

    Returns 403. Use when the user cannot perform the action (e.g. does
    not own the resource, lacks role). Typo "Forbiden" preserved for
    backwards compatibility.

    Examples:
        >>> raise ForbidenError("User does not own this vehicle")
        >>> raise ForbidenError("API key has been deactivated", session=session)
    """

    pass


def init_errors(app):
    """Register Flask error handlers for all custom and common exceptions.

    Call once during app initialization (e.g. in create_app). Handlers
    return standard_response() with appropriate status codes.

    Examples:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> init_errors(app)
    """
    @app.errorhandler(409)
    def conflict_error(error):
        logger.error("HTTP 409: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        return standard_response(
            error=True,
            ui_message="Conflict",
            status_code=409,
        )

    @app.errorhandler(PermissionError)
    def permission_error(error):
        logger.error("PermissionError: %s", error)
        return standard_response(
            error=True,
            ui_message="Insufficient Permissions",
            status_code=403,
        )

    @app.errorhandler(NotFoundError)
    def resource_not_found_error(error):
        logger.info("NotFoundError: %s", error)
        msg = str(error)
        return standard_response(error=True, ui_message=msg, status_code=404)

    @app.errorhandler(DataNotFoundError)
    def data_not_found_error(error):
        logger.info("DataNotFoundError: %s", error)
        msg = str(error)
        return standard_response(error=True, ui_message=msg, status_code=404)

    @app.errorhandler(ForbidenError)
    def forbiden_error(error):
        logger.error("ForbidenError: %s", error)
        return standard_response(
            error=True,
            ui_message=str(error),
            status_code=403,
        )

    @app.errorhandler(VehicleError)
    def vehicle_error(error):
        logger.error("VehicleError: %s", error)
        return standard_response(error=True, ui_message=str(error), status_code=400)

    @app.errorhandler(AuthenticationError)
    def authentication_error(error):
        logger.error("AuthenticationError: %s", error)
        msg = str(error)
        return standard_response(error=True, ui_message=msg, status_code=401)

    @app.errorhandler(ValidationError)
    def validation_error(error):
        errors = []
        for field, messages in error.messages.items():
            if isinstance(messages, list):
                errors.extend([f"{field}: {msg}" for msg in messages])
            else:
                errors.append(f"{field}: {messages}")
        error_message = "; ".join(errors) if errors else "Validation error"
        logger.error("ValidationError: %s", error_message)
        return standard_response(
            error=True,
            ui_message=error_message,
            status_code=400,
        )

    @app.errorhandler(ValueError)
    def value_error(error):
        logger.error("ValueError: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        return standard_response(error=True, ui_message=str(error), status_code=400)

    @app.errorhandler(AlreadyExistsError)
    def resource_exist_error(error):
        logger.error("AlreadyExistsError: %s", error)
        msg = str(error)
        return standard_response(
            error=True,
            ui_message=msg,
            status_code=409,
        )

    @app.errorhandler(DataError)
    def data_error(error):
        logger.error("DataError: %s", error)
        return standard_response(
            error=True,
            ui_message="Invalid data provided.",
            status_code=400,
        )

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        logger.error("IntegrityError: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        msg = str(error)
        if "unique" in str(error).lower():
            msg = "Object already exists."
        return standard_response(
            error=True,
            ui_message=msg,
            status_code=409,
        )

    @app.errorhandler(OperationalError)
    def operational_error(error):
        msg = str(error)
        logger.error("OperationalError: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        return standard_response(
            error=True,
            dev_message=f"Database Error: {msg}",
            ui_message="Database Error",
            status_code=500,
        )

    @app.errorhandler(DatabaseError)
    def database_error_handler(error):
        logger.error("DatabaseError: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        msg = str(error)
        if "unique" in str(error).lower():
            msg = "Object already exists."
        return standard_response(
            error=True,
            ui_message=msg,
            status_code=409,
        )

    @app.errorhandler(500)
    def server_error(error):
        logger.error("HTTP 500: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        return standard_response(
            error=True,
            ui_message="Internal Server Error",
            status_code=500,
        )

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error("Unhandled exception: %s", e)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        if isinstance(e, HTTPException):
            return e
        dev_msg = ""
        if DEBUG:
            dev_msg = traceback_info if traceback_info else str(e)
        return standard_response(
            error=True,
            ui_message="Internal Server Error",
            dev_message=dev_msg,
            status_code=500,
        )

    @app.errorhandler(StripeError)
    def stripe_error(error):
        msg = str(error)
        logger.error("StripeError: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        return standard_response(
            error=True,
            ui_message=msg,
            status_code=404,
        )

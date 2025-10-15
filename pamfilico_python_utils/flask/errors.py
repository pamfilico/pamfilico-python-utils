import logging
import traceback

from marshmallow.exceptions import ValidationError
from sqlalchemy.exc import DataError, IntegrityError, OperationalError
from werkzeug.exceptions import HTTPException

from pamfilico_python_utils.flask.responses import standard_response

logger = logging.getLogger(__name__)

DEBUG = True  # global variable setting the debug config


class BaseError(Exception):
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
    pass


class DataNotFoundError(BaseError):
    pass


class QueueError(BaseError):
    pass


class VehicleError(BaseError):
    pass


class SubscriptionExpiredError(BaseError):
    pass


class InsuranceError(BaseError):
    pass


class LocationError(BaseError):
    pass


class AlreadyExistsError(BaseError):
    pass


class NotFoundError(BaseError):
    pass


class ServerError(BaseError):
    pass


class DatabaseError(BaseError):
    pass


class AuthenticationError(BaseError):
    pass


class EnvironmentVariableError(BaseError):
    pass


class EmailError(BaseError):
    pass


class StripeError(BaseError):
    pass


class ForbidenError(BaseError):
    pass


class ResourceExistsError(BaseError):
    pass


class UnknownException(BaseError):
    pass


class TokenError(BaseError):
    pass


class NotAuthorizedToView(BaseError):
    pass


# Car Errors
class CarIsCurrentlyBookedError(BaseError):
    pass


class CarHasPendingBookingsError(BaseError):
    pass


# Booking Errors
class BookingNotFoundError(BaseError):
    pass


class BookingHasPaymentError(BaseError):
    pass


# Customer Errors
class CustomerNotFoundError(BaseError):
    pass


class CustomerHasBookingError(BaseError):
    pass


class PaymentsExistError(BaseError):
    pass


class PaymentHasBookingError(BaseError):
    pass


def init_errors(app):
    @app.errorhandler(409)
    def conflict_error(error):
        logger.error(error)
        traceback.print_exc()
        return standard_response(
            error=True,
            message="Conflict",
            ui_message="Conflict",
            status_code=409,
        )

    @app.errorhandler(PermissionError)
    def permission_error(error):
        return standard_response(
            error=True,
            message="Insuficient Permissions",
            ui_message="Insuficient Permissions",
            status_code=403,
        )

    @app.errorhandler(NotFoundError)
    def resource_not_found_error(error):
        logger.info("NotFoundError: %s", error)
        msg = str(error)
        return standard_response(error=True, ui_message=msg, status_code=404)

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
        logger.error(error.messages)
        print(error.messages)
        errors = []
        for field, messages in error.messages.items():
            if isinstance(messages, list):
                errors.extend([f"{field}: {msg}" for msg in messages])
            else:
                errors.append(f"{field}: {messages}")
        error_message = "; ".join(errors) if errors else "Validation error"
        return standard_response(
            error=True,
            message=error_message,
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
        logger.error("ResourceExistsError: %s", error)
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
        msg = str(error)
        return standard_response(
            error=True,
            message=msg,
            ui_message="Conflict",
            status_code=409,
        )

    @app.errorhandler(OperationalError)
    def operational_error(error):
        msg = str(error)
        logger.error(error)
        return standard_response(
            error=True,
            message=f"Database Error: {msg}",
            ui_message="Database Error",
            status_code=500,
        )

    @app.errorhandler(DatabaseError)
    def database_error_handler(error):
        logger.error("DatabaseError: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        msg = str(error)
        if "unique" in str(error):
            msg = "Object already exists."
        return standard_response(
            error=True,
            ui_message=msg,
            status_code=409,
        )

    @app.errorhandler(500)
    def server_error(error):
        logger.error(error)
        return standard_response(
            error=True,
            message=str(error),
            ui_message="Internal Server Error",
            status_code=500,
        )

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(e)
        traceback.print_exc()
        if isinstance(e, HTTPException):
            return e
        print(e)
        res = {
            "code": 500,
            "errorType": "Internal Server Error",
            "errorMessage": "Something went really wrong!",
        }
        if DEBUG:
            res["errorMessage"] = e if hasattr(e, "message") else f"{e}"

        return standard_response(
            error=True,
            message=str(res.get("errorMessage", "Internal Server Error")),
            ui_message="Internal Server Error",
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

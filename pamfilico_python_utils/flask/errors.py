import logging
import traceback

from marshmallow.exceptions import ValidationError
from sqlalchemy.exc import DataError, IntegrityError
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


def init_errors(app):
    @app.errorhandler(NotFoundError)
    def resource_not_found_error(error):
        logger.info("NotFoundError: %s", error)
        msg = str(error)
        return standard_response(error=True, ui_message=msg, status_code=404)

    @app.errorhandler(VehicleError)
    def vehicle_error(error):
        logger.error("VehicleError: %s", error)
        return standard_response(ui_message=str(error), status_code=400)

    @app.errorhandler(AuthenticationError)
    def authentication_error(error):
        logger.error("AuthenticationError: %s", error)
        msg = str(error)
        return standard_response(error=True, ui_message=msg, status_code=401)

    @app.errorhandler(ValidationError)
    def validation_error(error):
        logger.error("ValidationError: %s", error)
        return standard_response(ui_message=str(error), status_code=400)

    @app.errorhandler(ValueError)
    def value_error(error):
        logger.error("ValueError: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        return standard_response(ui_message=str(error), status_code=400)

    @app.errorhandler(AlreadyExistsError)
    def resource_exist_error(error):
        logger.error("ResourceExistsError: %s", error)
        msg = str(error)
        return standard_response(
            ui_message=msg,
            status_code=409,
        )

    @app.errorhandler(DataError)
    def data_error(error):
        logger.error("DataError: %s", error)
        return standard_response(
            ui_message="Invalid data provided.",
            status_code=400,
        )

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        logger.error("IntegrityError: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        msg = str(error)
        if "unique" in str(error):
            msg = "Object already exists."
        return standard_response(
            ui_message=msg,
            status_code=409,
        )

    @app.errorhandler(DatabaseError)
    def integrity_errosr(error):
        logger.error("IntegrityError: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        msg = str(error)
        if "unique" in str(error):
            msg = "Object already exists."
        return standard_response(
            ui_message=msg,
            status_code=409,
        )

    @app.errorhandler(500)
    def server_error(error):
        logger.error("500Error: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        return standard_response(
            ui_message="Internal Server Error",
            status_code=500,
        )

    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.error("Exception: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        if isinstance(error, HTTPException):
            return error
        res = {
            "code": 500,
            "errorType": "Internal Server Error",
            "errorMessage": "Something went really wrong!",
            # "traceback": tb,
        }
        traceback_info = traceback.format_exc()
        if DEBUG:
            msg = f"{error} - Traceback: {traceback_info}"
            res["errorMessage"] = msg
        logger.error("Exception: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        return standard_response(
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
            ui_message=msg,
            status_code=404,
        )

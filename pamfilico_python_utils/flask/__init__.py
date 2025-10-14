"""Flask utilities for routing, authentication, and error handling."""

from pamfilico_python_utils.flask.auth import (
    admin_required,
    decode_jwe_token,
    encode_jwe,
    jwt_authenticator_with_scopes,
    validate_uuid_params,
)
from pamfilico_python_utils.flask.errors import (
    AlreadyExistsError,
    AuthenticationError,
    BaseError,
    BizlogicError,
    DatabaseError,
    DataNotFoundError,
    EmailError,
    EnvironmentVariableError,
    InsuranceError,
    LocationError,
    NotFoundError,
    QueueError,
    ServerError,
    StripeError,
    SubscriptionExpiredError,
    VehicleError,
    init_errors,
)
from pamfilico_python_utils.flask.responses import standard_response

__all__ = [
    # Auth
    "admin_required",
    "decode_jwe_token",
    "encode_jwe",
    "jwt_authenticator_with_scopes",
    "validate_uuid_params",
    # Errors
    "AlreadyExistsError",
    "AuthenticationError",
    "BaseError",
    "BizlogicError",
    "DatabaseError",
    "DataNotFoundError",
    "EmailError",
    "EnvironmentVariableError",
    "InsuranceError",
    "LocationError",
    "NotFoundError",
    "QueueError",
    "ServerError",
    "StripeError",
    "SubscriptionExpiredError",
    "VehicleError",
    "init_errors",
    # Responses
    "standard_response",
]

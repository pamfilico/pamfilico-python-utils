"""Test that all public imports resolve and key attributes exist."""


def test_flask_imports():
    from pamfilico_python_utils.flask import (
        init_errors,
        standard_response,
        init_user_auth,
        jwt_authenticator_with_scopes,
        decode_jwe_token,
        encode_jwe,
        configure_authenticatenext,
        authenticatenext,
    )

    assert callable(init_errors)
    assert callable(standard_response)
    assert callable(init_user_auth)


def test_flask_errors_imports():
    from pamfilico_python_utils.flask.errors import (
        BaseError,
        NotFoundError,
        DataNotFoundError,
        AuthenticationError,
        BizlogicError,
        ForbidenError,
        ServerError,
        DatabaseError,
        EnvironmentVariableError,
    )

    assert BaseError
    assert NotFoundError
    assert AuthenticationError


def test_flask_pagination_import():
    from pamfilico_python_utils.flask.pagination import collection

    assert callable(collection)


def test_sqlalchemy_mixins_import():
    from pamfilico_python_utils.sqlalchemy.auth import (
        NextAuthUserMixin,
        NextAuthSessionMixin,
        NextAuthAccountMixin,
        NextAuthVerificationTokenMixin,
    )

    assert hasattr(NextAuthUserMixin, "email_verified")
    assert hasattr(NextAuthUserMixin, "emailVerified")
    assert hasattr(NextAuthSessionMixin, "sessionToken")
    assert hasattr(NextAuthAccountMixin, "provider_account_id")


def test_sqlalchemy_filtering_import():
    from pamfilico_python_utils.sqlalchemy import apply_filters, parse_filters

    assert callable(apply_filters)
    assert callable(parse_filters)

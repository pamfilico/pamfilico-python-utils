"""Tests for init_errors and error handler responses."""

from flask import Flask

from pamfilico_python_utils.flask import init_errors
from pamfilico_python_utils.flask.errors import (
    AuthenticationError,
    ForbidenError,
    NotFoundError,
)


def test_init_errors_registers_handlers(flask_app):
    init_errors(flask_app)

    @flask_app.route("/404")
    def fail():
        raise NotFoundError("Not found")

    with flask_app.test_client() as c:
        r = c.get("/404")
        assert r.status_code == 404
        data = r.get_json()
        assert data["error"] is True
        assert "ui_message" in data or "message" in data or "data" in data


def test_error_handlers_return_standard_shape(flask_app):
    init_errors(flask_app)

    @flask_app.route("/notfound")
    def nf():
        raise NotFoundError("x")

    @flask_app.route("/forbidden")
    def fb():
        raise ForbidenError("x")

    @flask_app.route("/auth")
    def au():
        raise AuthenticationError("x")

    with flask_app.test_client() as c:
        for path, expected_code in [
            ("/notfound", 404),
            ("/forbidden", 403),
            ("/auth", 401),
        ]:
            r = c.get(path)
            assert r.status_code == expected_code
            data = r.get_json()
            assert "error" in data
            assert data["error"] is True

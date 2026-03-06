"""Tests for init_user_auth blueprint registration."""

from flask import Flask

from pamfilico_python_utils.flask import init_errors, init_user_auth


def test_init_user_auth_registers_routes(flask_app, mock_db_session):
    class MockUser:
        pass

    class MockSession:
        pass

    class MockAccount:
        pass

    class MockVT:
        pass

    init_errors(flask_app)
    init_user_auth(
        flask_app,
        lambda: mock_db_session(),
        MockUser,
        MockSession,
        MockAccount,
        MockVT,
        url_prefix="/api/v2/auth",
    )

    rules = [r.rule for r in flask_app.url_map.iter_rules() if "v2/auth" in r.rule]
    assert len(rules) >= 7

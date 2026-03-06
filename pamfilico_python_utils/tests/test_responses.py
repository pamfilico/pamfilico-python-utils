"""Tests for standard_response API spec compliance."""

from pamfilico_python_utils.flask import standard_response


def test_success_response():
    r, code = standard_response(data={"item": "value"}, ui_message="Saved!")
    assert r["data"] == {"item": "value"}
    assert r["error"] is False
    assert "dev_message" not in r or r.get("dev_message") == ""


def test_error_response_with_dev_message():
    r, _ = standard_response(
        error=True, ui_message="Not found", dev_message="debug"
    )
    assert r["error"] is True
    assert r["dev_message"] == "debug"


def test_response_with_pagination_and_ordering():
    r, _ = standard_response(
        data=[{"id": 1}],
        pagination={
            "currentPage": 1,
            "totalPages": 5,
            "pageSize": 20,
            "totalCount": 100,
            "nextPage": 2,
            "previousPage": None,
        },
        ordering={"sortBy": "created_at", "sortOrder": "desc"},
    )
    assert r["pagination"]["currentPage"] == 1
    assert r["ordering"]["sortBy"] == "created_at"

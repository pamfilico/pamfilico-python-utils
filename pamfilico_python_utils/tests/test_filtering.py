"""
Tests for apply_filters() and parse_filters().

Covers: all operators (eq, ne, gt, gte, lt, lte, contains, in),
type coercion (int, float, bool, date, datetime, string),
allowed_fields whitelist, unknown fields, combined filters,
and the filtering echo dict.
"""
from datetime import date, datetime

from flask import request

from pamfilico_python_utils.sqlalchemy.filtering import apply_filters, parse_filters
from pamfilico_python_utils.tests.conftest import Item


def _query_with_filters(filter_app, filter_session, params, allowed_fields=None):
    """Run apply_filters inside a Flask request context."""
    with filter_app.test_request_context(
        f"/?{'&'.join(f'{k}={v}' for k, v in params.items())}"
    ):
        query = filter_session.query(Item)
        filtered_query, active_filters = apply_filters(
            query, Item, request.args, allowed_fields=allowed_fields
        )
        results = filtered_query.all()
    return results, active_filters


# --- parse_filters ---


class TestParseFilters:
    def test_parses_valid_filters(self):
        args = {"filter[status][eq]": "active", "filter[price][gte]": "100"}
        parsed = parse_filters(args)
        assert len(parsed) == 2
        assert {"field": "status", "operator": "eq", "value": "active"} in parsed
        assert {"field": "price", "operator": "gte", "value": "100"} in parsed

    def test_ignores_non_filter_params(self):
        args = {"page": "1", "per_page": "20", "filter[status][eq]": "active"}
        parsed = parse_filters(args)
        assert len(parsed) == 1

    def test_ignores_unknown_operators(self):
        args = {"filter[status][like]": "active"}
        parsed = parse_filters(args)
        assert len(parsed) == 0

    def test_empty_args(self):
        assert parse_filters({}) == []


# --- eq operator ---


class TestEqOperator:
    def test_string_eq(self, filter_app, filter_session):
        results, filters = _query_with_filters(
            filter_app, filter_session, {"filter[status][eq]": "active"}
        )
        assert len(results) == 3
        assert all(r.status == "active" for r in results)
        assert filters == {"status": {"eq": "active"}}

    def test_int_eq(self, filter_app, filter_session):
        results, _ = _query_with_filters(
            filter_app, filter_session, {"filter[quantity][eq]": "5"}
        )
        assert len(results) == 1
        assert results[0].name == "Gaming Laptop"

    def test_bool_eq_true(self, filter_app, filter_session):
        results, _ = _query_with_filters(
            filter_app, filter_session, {"filter[is_active][eq]": "true"}
        )
        assert len(results) == 4
        assert all(r.is_active for r in results)

    def test_bool_eq_false(self, filter_app, filter_session):
        results, _ = _query_with_filters(
            filter_app, filter_session, {"filter[is_active][eq]": "false"}
        )
        assert len(results) == 1
        assert results[0].name == "Broken Monitor"


# --- ne operator ---


class TestNeOperator:
    def test_string_ne(self, filter_app, filter_session):
        results, filters = _query_with_filters(
            filter_app, filter_session, {"filter[status][ne]": "deleted"}
        )
        assert len(results) == 4
        assert all(r.status != "deleted" for r in results)
        assert filters == {"status": {"ne": "deleted"}}


# --- gt / gte / lt / lte operators (numeric) ---


class TestComparisonOperators:
    def test_gt_float(self, filter_app, filter_session):
        results, _ = _query_with_filters(
            filter_app, filter_session, {"filter[price][gt]": "300"}
        )
        assert all(r.price > 300 for r in results)
        assert len(results) == 2

    def test_gte_float(self, filter_app, filter_session):
        results, _ = _query_with_filters(
            filter_app, filter_session, {"filter[price][gte]": "300"}
        )
        assert all(r.price >= 300 for r in results)
        assert len(results) == 3

    def test_lt_int(self, filter_app, filter_session):
        results, _ = _query_with_filters(
            filter_app, filter_session, {"filter[quantity][lt]": "10"}
        )
        assert all(r.quantity < 10 for r in results)
        assert len(results) == 2

    def test_lte_int(self, filter_app, filter_session):
        results, _ = _query_with_filters(
            filter_app, filter_session, {"filter[quantity][lte]": "10"}
        )
        assert all(r.quantity <= 10 for r in results)
        assert len(results) == 3

    def test_range_filter(self, filter_app, filter_session):
        results, filters = _query_with_filters(
            filter_app,
            filter_session,
            {"filter[price][gte]": "100", "filter[price][lte]": "500"},
        )
        assert all(100 <= r.price <= 500 for r in results)
        assert len(results) == 2
        assert filters == {"price": {"gte": "100", "lte": "500"}}


# --- gt / lt with dates ---


class TestDateFilters:
    def test_date_gte(self, filter_app, filter_session):
        results, _ = _query_with_filters(
            filter_app, filter_session, {"filter[created_date][gte]": "2025-03-01"}
        )
        assert all(r.created_date >= date(2025, 3, 1) for r in results)
        assert len(results) == 2

    def test_datetime_lt(self, filter_app, filter_session):
        results, _ = _query_with_filters(
            filter_app,
            filter_session,
            {"filter[created_at][lt]": "2025-01-16T00:00:00"},
        )
        assert all(r.created_at < datetime(2025, 1, 16) for r in results)
        assert len(results) == 2


# --- contains operator ---


class TestContainsOperator:
    def test_contains_case_insensitive(self, filter_app, filter_session):
        results, filters = _query_with_filters(
            filter_app, filter_session, {"filter[name][contains]": "laptop"}
        )
        assert len(results) == 2
        assert all("laptop" in r.name.lower() for r in results)
        assert filters == {"name": {"contains": "laptop"}}

    def test_contains_partial(self, filter_app, filter_session):
        results, _ = _query_with_filters(
            filter_app, filter_session, {"filter[name][contains]": "key"}
        )
        assert len(results) == 1
        assert results[0].name == "Mechanical Keyboard"


# --- in operator ---


class TestInOperator:
    def test_in_strings(self, filter_app, filter_session):
        results, filters = _query_with_filters(
            filter_app, filter_session, {"filter[status][in]": "active,pending"}
        )
        assert len(results) == 4
        assert all(r.status in ("active", "pending") for r in results)
        assert filters == {"status": {"in": "active,pending"}}

    def test_in_integers(self, filter_app, filter_session):
        results, _ = _query_with_filters(
            filter_app, filter_session, {"filter[quantity][in]": "5,100"}
        )
        assert len(results) == 2
        assert {r.quantity for r in results} == {5, 100}


# --- allowed_fields whitelist ---


class TestAllowedFields:
    def test_allowed_fields_permits(self, filter_app, filter_session):
        results, filters = _query_with_filters(
            filter_app,
            filter_session,
            {"filter[status][eq]": "active"},
            allowed_fields={"status", "price"},
        )
        assert len(results) == 3
        assert filters == {"status": {"eq": "active"}}

    def test_allowed_fields_blocks(self, filter_app, filter_session):
        results, filters = _query_with_filters(
            filter_app,
            filter_session,
            {"filter[status][eq]": "active"},
            allowed_fields={"price"},
        )
        assert len(results) == 5
        assert filters is None

    def test_mixed_allowed_and_blocked(self, filter_app, filter_session):
        results, filters = _query_with_filters(
            filter_app,
            filter_session,
            {"filter[status][eq]": "active", "filter[price][gt]": "500"},
            allowed_fields={"price"},
        )
        assert all(r.price > 500 for r in results)
        assert filters == {"price": {"gt": "500"}}


# --- edge cases ---


class TestEdgeCases:
    def test_unknown_field_ignored(self, filter_app, filter_session):
        results, filters = _query_with_filters(
            filter_app, filter_session, {"filter[nonexistent][eq]": "x"}
        )
        assert len(results) == 5
        assert filters is None

    def test_no_filters_returns_none(self, filter_app, filter_session):
        results, filters = _query_with_filters(filter_app, filter_session, {"page": "1"})
        assert len(results) == 5
        assert filters is None

    def test_multiple_fields_combined(self, filter_app, filter_session):
        results, filters = _query_with_filters(
            filter_app,
            filter_session,
            {
                "filter[status][eq]": "active",
                "filter[category][eq]": "electronics",
                "filter[price][gte]": "100",
            },
        )
        assert len(results) == 2
        assert filters == {
            "status": {"eq": "active"},
            "category": {"eq": "electronics"},
            "price": {"gte": "100"},
        }

    def test_non_filter_params_ignored(self, filter_app, filter_session):
        results, filters = _query_with_filters(
            filter_app,
            filter_session,
            {
                "page": "1",
                "per_page": "20",
                "sort_by": "created_at",
                "filter[status][eq]": "active",
            },
        )
        assert len(results) == 3
        assert filters == {"status": {"eq": "active"}}

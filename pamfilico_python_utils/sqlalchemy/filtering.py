"""
Apply filter[field][operator]=value query params to SQLAlchemy queries.

Values are coerced to the column's Python type. Use with standard_response(filtering=...).
"""
import re
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, Numeric, inspect as sa_inspect

FILTER_OPERATORS = {
    "eq": lambda col, val: col == val,
    "ne": lambda col, val: col != val,
    "gt": lambda col, val: col > val,
    "gte": lambda col, val: col >= val,
    "lt": lambda col, val: col < val,
    "lte": lambda col, val: col <= val,
    "contains": lambda col, val: col.ilike(f"%{val}%"),
    "in": lambda col, val: col.in_(val if isinstance(val, list) else val.split(",")),
}

FILTER_PATTERN = re.compile(r"^filter\[(\w+)\]\[(\w+)\]$")


def _coerce_value(value, column_type):
    """Coerce string value to Python type matching the SQLAlchemy column."""
    if isinstance(column_type, (Integer,)):
        return int(value)
    if isinstance(column_type, (Float, Numeric)):
        return float(value)
    if isinstance(column_type, Boolean):
        return value.lower() in ("true", "1", "yes")
    if isinstance(column_type, DateTime):
        return datetime.fromisoformat(value)
    if isinstance(column_type, Date):
        return date.fromisoformat(value)
    return value


def parse_filters(request_args):
    """Parse filter[field][operator]=value query params into a list of filter dicts."""
    filters = []
    for key, value in request_args.items():
        match = FILTER_PATTERN.match(key)
        if match:
            field, operator = match.groups()
            if operator in FILTER_OPERATORS:
                filters.append({"field": field, "operator": operator, "value": value})
    return filters


def apply_filters(query, model_class, request_args, allowed_fields=None):
    """
    Apply filter[field][operator]=value query params to a SQLAlchemy query.

    Values are coerced to the column's Python type. Returns active_filters dict
    for standard_response(filtering=...).

    Args:
        query: SQLAlchemy query object
        model_class: The SQLAlchemy model class
        request_args: request.args (ImmutableMultiDict)
        allowed_fields: Optional set of field names to allow (whitelist).
                       If None, all model columns are allowed.

    Returns:
        Tuple of (filtered_query, active_filters_dict or None)
    """
    parsed = parse_filters(request_args)
    active_filters = {}

    mapper = sa_inspect(model_class)
    column_types = {col.key: col.type for col in mapper.columns}

    for f in parsed:
        field, operator, value = f["field"], f["operator"], f["value"]

        if allowed_fields and field not in allowed_fields:
            continue
        if field not in column_types:
            continue

        column = getattr(model_class, field)
        col_type = column_types[field]
        if operator == "in":
            raw_parts = value.split(",") if isinstance(value, str) else value
            value = [_coerce_value(v.strip(), col_type) for v in raw_parts]
        elif operator != "contains":
            value = _coerce_value(value, col_type)

        condition = FILTER_OPERATORS[operator](column, value)
        query = query.filter(condition)

        if field not in active_filters:
            active_filters[field] = {}
        active_filters[field][operator] = f["value"]

    return query, active_filters if active_filters else None

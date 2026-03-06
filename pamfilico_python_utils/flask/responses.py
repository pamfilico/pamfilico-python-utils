"""
Standard API response envelope.

Matches docs/api/spec.md canonical version. All Flask API responses should use
``standard_response()`` for a consistent JSON shape (error, ui_message,
status_code, redirect_to_login, data, plus opt-in dev_message, pagination,
ordering, filtering).

Examples
--------
Success with data::

    from pamfilico_python_utils.flask.responses import standard_response

    @app.route("/api/user")
    def get_user():
        user = fetch_current_user()
        return standard_response(data={"id": user.id, "email": user.email})

Error response (e.g. in route or error handler)::

    return standard_response(
        error=True,
        ui_message="Vehicle not found",
        status_code=404,
    )

Error with developer context (for debugging)::

    return standard_response(
        error=True,
        ui_message="Internal Server Error",
        dev_message=f"Traceback: {traceback.format_exc()}",
        status_code=500,
    )

Paginated list with ordering::

    return standard_response(
        data=items,
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

Paginated list with filtering metadata::

    return standard_response(
        data=items,
        pagination={...},
        ordering={...},
        filtering={"status": {"eq": "active"}, "price": {"gte": "10"}},
    )

Auth redirect hint::

    return standard_response(
        error=True,
        ui_message="Session expired",
        redirect_to_login=True,
        status_code=401,
    )
"""


def standard_response(
    data=None,
    ui_message="",
    dev_message="",
    status_code=200,
    error=False,
    redirect_to_login=False,
    pagination=None,
    ordering=None,
    filtering=None,
):
    """Wrap an API response in the standard envelope.

    Parameters
    ----------
    data : optional
        The response payload. Defaults to None.
    ui_message : str, optional
        User-facing message displayed in the UI (toast, alert). Defaults to "".
    dev_message : str, optional
        Developer-facing message for debugging (only included when non-empty).
        Defaults to "".
    status_code : int, optional
        HTTP status code. Defaults to 200.
    error : bool, optional
        True if the request failed, False if it succeeded. Defaults to False.
    redirect_to_login : bool, optional
        Hint for the frontend to redirect to login. Defaults to False.
    pagination : dict, optional
        Pagination metadata (only included when provided).
        Keys: currentPage, totalPages, pageSize, totalCount, nextPage, previousPage.
    ordering : dict, optional
        Ordering metadata (only included when provided).
        Keys: sortBy, sortOrder.
    filtering : dict, optional
        Active filter metadata (only included when provided).

    Returns
    -------
    tuple[dict, int]
        (response_dict, status_code) for Flask to jsonify and return.

    Examples
    --------
    >>> response, code = standard_response(data={"item": "value"}, ui_message="Saved!")
    >>> response["data"]
    {'item': 'value'}
    >>> response["error"]
    False
    >>> "dev_message" in response
    False
    >>> "pagination" in response
    False

    >>> response, _ = standard_response(
    ...     error=True, ui_message="Not found", dev_message="user_id=abc has no items"
    ... )
    >>> response["error"]
    True
    >>> response["dev_message"]
    'user_id=abc has no items'

    >>> response, _ = standard_response(
    ...     data=[{"id": 1}],
    ...     pagination={"currentPage": 1, "totalPages": 5, "pageSize": 20,
    ...                "totalCount": 100, "nextPage": 2, "previousPage": None},
    ...     ordering={"sortBy": "created_at", "sortOrder": "desc"},
    ... )
    >>> response["pagination"]["currentPage"]
    1
    >>> response["ordering"]["sortBy"]
    'created_at'
    """
    response = {
        "error": error,
        "ui_message": ui_message,
        "status_code": status_code,
        "redirect_to_login": redirect_to_login,
        "data": data,
    }

    if dev_message:
        response["dev_message"] = dev_message

    if pagination is not None:
        response["pagination"] = pagination

    if ordering is not None:
        response["ordering"] = ordering

    if filtering is not None:
        response["filtering"] = filtering

    return response, status_code

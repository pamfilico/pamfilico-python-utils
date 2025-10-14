from typing import List


# TODO: include other fields
def standard_response(
    data=None,
    ui_message="",
    status_code: int = 200,
    redirect_to_login: bool = False,
    excluded_keys: List[str] = [
        "pagination",
        "meta",
        "rateLimit",
        "_links",
        "requestInfo",
        "debugInfo",
        "warnings",
        "locale",
        "timezone",
        "authToken",
        "success",
        "dev_message",
    ],
    error: bool = False,
    message: str = "",
    dev_message: str = "",
):
    """
    Generates a standard response dictionary with various fields and a status code.

    Parameters:
    - data (optional): The data to be included in the response. Defaults to None.
    - ui_message (str, optional): A user interface message. Defaults to an empty string.
    - status_code (int, optional): The HTTP status code for the response. Defaults to 200.
    - excluded_keys (list, optional): A list of keys to exclude from the response. Defaults to None.

    Returns:
    - tuple: A tuple containing the response dictionary and the status code.

    Doctests:
    >>> response, code = standard_response(
    ...     data={"item": "value"}, ui_message="Test Message", status_code=200
    ... )
    >>> response["ui_message"]
    'Test Message'
    >>> response["data"]
    {'item': 'value'}
    >>> code
    200

    >>> response, _ = standard_response(excluded_keys=["data", "meta"])
    >>> "data" in response
    False
    >>> "meta" in response
    False
    """

    if excluded_keys is None:
        excluded_keys = []

    response_template = {
        "message": message,
        "error": error,
        "redirect_to_login": redirect_to_login,
        "ui_message": ui_message,
        "dev_message": dev_message,
        "status_code": status_code,
        "data": data,
        "pagination": {
            "page_number": None,
            "results_per_page": None,
            "total_count": None,
            "total_pages": None,
            "has_next": None,
            "has_prev": None,
        },
        "meta": {"apiVersion": None, "responseTime": None, "fromCache": None},
        "rateLimit": {
            "limit": None,
            "remaining": None,
            "reset": None,
        },
        "warnings": [],
        "locale": None,
        "timezone": None,
        "authToken": None,
        "_links": {
            "self": None,
            "next": None,
            "previous": None,
        },
        "requestInfo": {},
        "debugInfo": {"stackTrace": None},
    }

    # Remove excluded keys
    for key in excluded_keys:
        response_template.pop(key, None)

    return response_template, status_code

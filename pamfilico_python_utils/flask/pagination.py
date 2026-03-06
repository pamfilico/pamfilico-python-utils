"""Pagination decorator for Flask API endpoints."""

from functools import wraps

from flask import request

from pamfilico_python_utils.flask.errors import ServerError
from pamfilico_python_utils.flask.responses import standard_response


def collection(MarshmallowSchema, searchable_fields=None, sortable_fields=None):
    """
    Decorator that automatically paginates SQLAlchemy query results with optional search and sorting.

    Uses standard_response and raises ValueError for validation errors (handled by init_errors).
    Pagination/ordering keys follow docs spec (camelCase).

    Args:
        MarshmallowSchema: A Marshmallow schema class for serialization
        searchable_fields (list): List of field names that can be searched (e.g., ['first_name', 'email'])
        sortable_fields (list): List of field names that can be sorted (e.g., ['first_name', 'created_at'])

    Query Parameters:
        results_per_page (int): Number of results per page (default: 10, max: 100)
        page_number (int): Page number to retrieve (default: 1)
        search_by (str): Field name to search by (must be in searchable_fields)
        search_value (str): Value to search for (case-insensitive partial match)
        order_by (str): Field name to sort by (must be in sortable_fields)
        order_direction (str): Sort direction - 'asc' or 'desc' (default: 'asc')

    Returns:
        standard_response with data, pagination (camelCase), ordering when applicable

    Raises:
        ValueError: Invalid pagination, search, or sort parameters (handled by init_errors)
        ServerError: Database or query execution failure

    Example:
        >>> from flask import Flask
        >>> from pamfilico_python_utils.flask import collection, jwt_authenticator_with_scopes
        >>> from your_app.models import Vehicle
        >>> from your_app.schemas import VehicleGetSchema
        >>>
        >>> app = Flask(__name__)
        >>> init_errors(app)
        >>>
        >>> @app.route('/api/vehicles')
        >>> @collection(
        ...     VehicleGetSchema,
        ...     searchable_fields=['name', 'license_plate'],
        ...     sortable_fields=['name', 'created_at']
        ... )
        >>> @jwt_authenticator_with_scopes(['user'])
        >>> def list_vehicles(auth):
        ...     return session.query(Vehicle).filter_by(user_id=auth['id'])
    """
    searchable_fields = searchable_fields or []
    sortable_fields = sortable_fields or []

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Extract auth from kwargs (injected by jwt_authenticator_with_scopes)
            auth = kwargs.get("auth")

            # Get pagination parameters from query string
            try:
                results_per_page = int(request.args.get("results_per_page", 10))
                page_number = int(request.args.get("page_number", 1))
            except ValueError:
                raise ValueError("Invalid pagination parameters. Must be integers.")

            # Get search parameters
            search_by = request.args.get("search_by", "").strip()
            search_value = request.args.get("search_value", "").strip()

            # Get sorting parameters
            order_by = request.args.get("order_by", "").strip()
            order_direction = request.args.get("order_direction", "asc").strip().lower()

            # Validate search parameters
            if search_by and search_by not in searchable_fields:
                raise ValueError(
                    f"Invalid search field. Allowed fields: {', '.join(searchable_fields)}"
                )

            # Validate sorting parameters
            if order_by and order_by not in sortable_fields:
                raise ValueError(
                    f"Invalid sort field. Allowed fields: {', '.join(sortable_fields)}"
                )

            if order_direction not in ["asc", "desc"]:
                raise ValueError("order_direction must be 'asc' or 'desc'")

            if results_per_page < 1 or results_per_page > 100:
                raise ValueError("results_per_page must be between 1 and 100")

            if page_number < 1:
                raise ValueError("page_number must be greater than 0")

            session = None
            try:
                # Call the original function (auth and URL params passed via kwargs/args)
                query = f(*args, **kwargs)

                # Get the model class from the query
                model_class = query.column_descriptions[0]["type"]

                # Apply search filter if provided
                if search_by and search_value:
                    if hasattr(model_class, search_by):
                        column = getattr(model_class, search_by)
                        query = query.filter(column.ilike(f"%{search_value}%"))
                    else:
                        raise ValueError(f"Field '{search_by}' not found in model")

                # Apply sorting if provided
                if order_by:
                    if hasattr(model_class, order_by):
                        column = getattr(model_class, order_by)
                        if order_direction == "desc":
                            query = query.order_by(column.desc())
                        else:
                            query = query.order_by(column.asc())
                    else:
                        raise ValueError(f"Field '{order_by}' not found in model")

                # Calculate offset
                offset = (page_number - 1) * results_per_page

                # Get total count after filters but before pagination
                total_count = query.count()

                # Apply pagination
                paginated_query = query.limit(results_per_page).offset(offset)

                # Execute query and get results
                results = paginated_query.all()

                # Get the session from the query object
                session = query.session

                # Serialize results (do this before closing session)
                schema = MarshmallowSchema(many=True)
                serialized_data = schema.dump(results)

            except (ValueError, ServerError):
                raise
            except Exception as e:
                if session:
                    try:
                        session.rollback()
                        session.close()
                    except Exception:
                        pass
                raise ServerError(f"Database error: {str(e)}", session=None)

            finally:
                if session:
                    session.close()

            # Calculate pagination metadata (camelCase per docs spec)
            total_pages = (total_count + results_per_page - 1) // results_per_page
            pagination_meta = {
                "currentPage": page_number,
                "totalPages": total_pages,
                "pageSize": results_per_page,
                "totalCount": total_count,
                "nextPage": page_number + 1 if page_number < total_pages else None,
                "previousPage": page_number - 1 if page_number > 1 else None,
            }
            ordering_meta = None
            if order_by:
                ordering_meta = {
                    "sortBy": order_by,
                    "sortOrder": order_direction,
                }

            return standard_response(
                data=serialized_data,
                pagination=pagination_meta,
                ordering=ordering_meta,
                status_code=200,
            )

        return wrapper

    return decorator

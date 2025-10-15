from functools import wraps
from flask import request, jsonify


def collection(MarshmallowSchema, searchable_fields=None, sortable_fields=None):
    """
    Decorator that automatically paginates SQLAlchemy query results with optional search and sorting.

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
        JSON response with paginated data and metadata

    Example:
        >>> from flask import Flask
        >>> from pamfilico_python_utils.flask import collection, jwt_authenticator_with_scopes
        >>> from your_app.models import Vehicle
        >>> from your_app.schemas import VehicleGetSchema
        >>>
        >>> app = Flask(__name__)
        >>>
        >>> @app.route('/api/vehicles')
        >>> @collection(
        ...     VehicleGetSchema,
        ...     searchable_fields=['name', 'license_plate'],
        ...     sortable_fields=['name', 'created_at']
        ... )
        >>> @jwt_authenticator_with_scopes(['user'])
        >>> def list_vehicles(auth):
        ...     # Return a SQLAlchemy query object
        ...     from your_app.database import session
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
                return (
                    jsonify(
                        {"error": "Invalid pagination parameters. Must be integers."}
                    ),
                    400,
                )

            # Get search parameters
            search_by = request.args.get("search_by", "").strip()
            search_value = request.args.get("search_value", "").strip()

            # Get sorting parameters
            order_by = request.args.get("order_by", "").strip()
            order_direction = request.args.get("order_direction", "asc").strip().lower()

            # Validate search parameters
            if search_by and search_by not in searchable_fields:
                return (
                    jsonify(
                        {
                            "error": f"Invalid search field. Allowed fields: {', '.join(searchable_fields)}"
                        }
                    ),
                    400,
                )

            # Validate sorting parameters
            if order_by and order_by not in sortable_fields:
                return (
                    jsonify(
                        {
                            "error": f"Invalid sort field. Allowed fields: {', '.join(sortable_fields)}"
                        }
                    ),
                    400,
                )

            if order_direction not in ["asc", "desc"]:
                return (
                    jsonify({"error": "order_direction must be 'asc' or 'desc'"}),
                    400,
                )

            # Validate parameters
            if results_per_page < 1 or results_per_page > 100:
                return (
                    jsonify({"error": "results_per_page must be between 1 and 100"}),
                    400,
                )

            if page_number < 1:
                return jsonify({"error": "page_number must be greater than 0"}), 400

            session = None  # Initialize for exception handler
            try:
                # Call the original function with auth parameter
                query = f(auth=auth)

                # Get the model class from the query
                model_class = query.column_descriptions[0]["type"]

                # Apply search filter if provided
                if search_by and search_value:
                    # Get the column attribute
                    if hasattr(model_class, search_by):
                        column = getattr(model_class, search_by)
                        # Apply case-insensitive LIKE search
                        query = query.filter(column.ilike(f"%{search_value}%"))
                    else:
                        return (
                            jsonify(
                                {"error": f"Field '{search_by}' not found in model"}
                            ),
                            400,
                        )

                # Apply sorting if provided
                if order_by:
                    if hasattr(model_class, order_by):
                        column = getattr(model_class, order_by)
                        # Apply sorting based on direction
                        if order_direction == "desc":
                            query = query.order_by(column.desc())
                        else:
                            query = query.order_by(column.asc())
                    else:
                        return (
                            jsonify(
                                {"error": f"Field '{order_by}' not found in model"}
                            ),
                            400,
                        )

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

            except Exception as e:
                # Close session on error
                if session:
                    session.close()
                return jsonify({"error": f"Database error: {str(e)}"}), 500

            finally:
                # Always close the session
                if session:
                    session.close()

            # Calculate pagination metadata
            total_pages = (total_count + results_per_page - 1) // results_per_page

            # Build response
            response = {
                "data": serialized_data,
                "pagination": {
                    "page_number": page_number,
                    "results_per_page": results_per_page,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page_number < total_pages,
                    "has_prev": page_number > 1,
                },
            }

            return jsonify(response), 200

        return wrapper

    return decorator

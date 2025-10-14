import uuid


def generate_uuid():
    """
    Generate a unique UUID.

    Returns:
        str: A string representation of a new UUID.
    """
    return str(uuid.uuid4())

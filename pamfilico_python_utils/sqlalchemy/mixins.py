from sqlalchemy import Column, DateTime, func


class DateTimeMixin:
    """
    Mixin class for adding `created_at` and `updated_at` fields to SQLAlchemy models.
    Both fields are timezone-aware datetime fields.
    """

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    The `created_at` field represents the time when the record was created.
    It defaults to the current time at the moment of record creation.
    """

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    """
    The `updated_at` field represents the time when the record was last updated.
    It updates to the current time every time the record is updated.
    """

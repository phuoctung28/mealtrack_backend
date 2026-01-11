import uuid

from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import declarative_mixin

from src.domain.services.timezone_utils import utc_now


@declarative_mixin
class PrimaryEntityMixin:
    """Base mixin for primary entities with GUID as primary key."""

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


@declarative_mixin
class SecondaryEntityMixin:
    """Base mixin for secondary entities with auto-incrementing ID."""

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


@declarative_mixin
class TimestampMixin:
    """Mixin that only provides timestamp fields without ID."""
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


# Maintain backward compatibility
BaseMixin = PrimaryEntityMixin 
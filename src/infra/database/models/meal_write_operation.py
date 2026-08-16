"""Durable idempotency records for authoritative meal writes."""

import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.base import Base


class MealWriteOperationORM(Base):
    """One user-scoped idempotency lease and its completed replay metadata."""

    __tablename__ = "meal_write_operation"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    operation = Column(String(64), nullable=False)
    idempotency_key = Column(String(255), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    status = Column(String(16), nullable=False, default="in_progress")
    lease_owner = Column(String(36), nullable=True)
    lease_generation = Column(Integer, nullable=False, default=1)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    target_meal_id = Column(String(36), nullable=True)
    response = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        Index(
            "uq_meal_write_operation_user_key",
            "user_id",
            "operation",
            "idempotency_key",
            unique=True,
        ),
        Index(
            "ix_meal_write_operation_status_updated_at",
            "status",
            "updated_at",
        ),
    )

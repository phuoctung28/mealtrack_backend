"""Persisted idempotent mutation responses for durable write replay."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, UniqueConstraint

from src.infra.database.base import Base
from src.infra.database.models.base import BaseMixin


class DurableWriteRecordORM(Base, BaseMixin):
    __tablename__ = "durable_write_records"

    user_id = Column(String(128), nullable=False)
    action = Column(String(64), nullable=False)
    idempotency_key = Column(String(160), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    response_status_code = Column(Integer, nullable=False)
    response_body_json = Column(Text, nullable=False)
    resource_id = Column(String(64), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "action",
            "idempotency_key",
            name="uq_durable_write_user_action_key",
        ),
        Index("ix_durable_write_records_expires_at", "expires_at"),
    )

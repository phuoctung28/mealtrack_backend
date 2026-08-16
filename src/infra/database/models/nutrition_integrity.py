"""Materialized nutrition-integrity control and append-only attribution rows."""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.domain.services.nutrition_integrity_policy import (
    NUTRITION_INTEGRITY_POLICY_VERSION,
)
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.base import Base


class FoodReferenceIntegrityControlModel(Base):
    """The single database-owned policy/generation control row."""

    __tablename__ = "food_reference_integrity_control"

    id = Column(Integer, primary_key=True, default=1)
    active_policy_version = Column(
        String(64), nullable=False, default=NUTRITION_INTEGRITY_POLICY_VERSION
    )
    catalog_integrity_generation = Column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    activation_run_id = Column(String(36), nullable=True)
    deployed_revision = Column(String(128), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class FoodReferenceIntegrityEventModel(Base):
    """Append-only state transition ledger without nutrition payloads or PII."""

    __tablename__ = "food_reference_integrity_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    food_reference_id = Column(
        Integer, ForeignKey("food_reference.id"), nullable=False, index=True
    )
    before_status = Column(String(16), nullable=False)
    after_status = Column(String(16), nullable=False)
    reason_code = Column(String(64), nullable=False)
    policy_version = Column(String(64), nullable=True)
    input_digest = Column(String(64), nullable=True)
    actor_kind = Column(String(32), nullable=False)
    reviewer_principal_hmac = Column(String(128), nullable=True)
    approval_reference = Column(String(255), nullable=True)
    run_id = Column(String(36), nullable=True)
    operation_id = Column(String(255), nullable=True)
    manifest_sha256 = Column(String(64), nullable=True)
    deployed_revision = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    food_reference = relationship("FoodReferenceModel")

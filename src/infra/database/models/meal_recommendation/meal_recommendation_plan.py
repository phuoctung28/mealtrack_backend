"""Database models for durable meal recommendation candidate rows."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import relationship

from src.infra.database.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class MealRecommendationORM(Base):
    """One candidate row in a three-day recommendation batch."""

    __tablename__ = "meal_recommendations"

    id = Column(String(36), primary_key=True, default=_uuid)
    batch_id = Column(String(36), nullable=False)
    slot_id = Column(String(36), nullable=False)
    recommendation_date = Column(Date, nullable=False)
    meal_type = Column(String(30), nullable=False)
    catalog_meal_id = Column(
        String(36),
        ForeignKey("meal_catalog.id", ondelete="RESTRICT"),
        nullable=False,
    )
    candidate_rank = Column(Integer, nullable=False)
    is_selected = Column(Boolean, nullable=False, default=False)
    score = Column(Numeric(10, 6), nullable=False)
    selection_version = Column(Integer, nullable=False, default=1)
    logged_at = Column(DateTime(timezone=True), nullable=True)
    logged_meal_id = Column(
        String(36),
        ForeignKey("meal.meal_id", ondelete="SET NULL"),
        nullable=True,
    )

    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    status = Column(String(20), nullable=True)
    timezone = Column(String(64), nullable=True)
    start_date = Column(Date, nullable=True)
    target_calories = Column(Integer, nullable=True)
    operation = Column(String(40), nullable=True)
    idempotency_key = Column(String(160), nullable=True)
    request_fingerprint = Column(String(64), nullable=True)
    superseded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    catalog_meal = relationship("MealCatalogORM", lazy="selectin")

    __table_args__ = (
        ForeignKeyConstraint(
            ["batch_id"],
            ["meal_recommendations.id"],
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')",
            name="ck_meal_recommendations_meal_type",
        ),
        CheckConstraint("candidate_rank >= 0", name="ck_meal_recommendations_rank"),
        CheckConstraint("score >= 0", name="ck_meal_recommendations_score"),
        CheckConstraint(
            "selection_version > 0",
            name="ck_meal_recommendations_selection_version",
        ),
        CheckConstraint(
            "(logged_at IS NULL AND logged_meal_id IS NULL) "
            "OR (logged_at IS NOT NULL AND logged_meal_id IS NOT NULL)",
            name="ck_meal_recommendations_logged_coherent",
        ),
        CheckConstraint(
            "("
            "id = batch_id AND user_id IS NOT NULL AND status IS NOT NULL "
            "AND timezone IS NOT NULL AND start_date IS NOT NULL "
            "AND target_calories IS NOT NULL "
            "AND operation IS NOT NULL AND idempotency_key IS NOT NULL "
            "AND request_fingerprint IS NOT NULL"
            ") OR ("
            "id <> batch_id AND user_id IS NULL AND status IS NULL "
            "AND timezone IS NULL AND start_date IS NULL "
            "AND target_calories IS NULL "
            "AND operation IS NULL AND idempotency_key IS NULL "
            "AND request_fingerprint IS NULL AND superseded_at IS NULL"
            ")",
            name="ck_meal_recommendations_anchor_metadata",
        ),
        CheckConstraint(
            "status IS NULL OR status IN ('active', 'superseded', 'failed')",
            name="ck_meal_recommendations_status",
        ),
        CheckConstraint(
            "target_calories IS NULL OR target_calories > 0",
            name="ck_meal_recommendations_target_calories",
        ),
        UniqueConstraint(
            "batch_id",
            "slot_id",
            "candidate_rank",
            name="uq_meal_recommendations_batch_slot_rank",
        ),
        UniqueConstraint(
            "batch_id",
            "slot_id",
            "catalog_meal_id",
            name="uq_meal_recommendations_batch_slot_catalog_meal",
        ),
        Index(
            "idx_meal_recommendations_anchor_user_created",
            "user_id",
            "created_at",
            postgresql_where=text("id = batch_id"),
        ),
        Index(
            "idx_meal_recommendations_batch_slot",
            "batch_id",
            "slot_id",
            "candidate_rank",
        ),
        Index(
            "uq_meal_recommendations_one_selected",
            "batch_id",
            "slot_id",
            unique=True,
            postgresql_where=text("is_selected"),
        ),
        Index(
            "uq_meal_recommendations_one_active_anchor",
            "user_id",
            "status",
            unique=True,
            postgresql_where=text("id = batch_id AND status = 'active'"),
        ),
        Index(
            "uq_meal_recommendations_anchor_idempotency",
            "user_id",
            "operation",
            "idempotency_key",
            unique=True,
            postgresql_where=text("id = batch_id"),
        ),
        Index(
            "uq_meal_recommendations_logged_meal",
            "logged_meal_id",
            unique=True,
            postgresql_where=text("logged_meal_id IS NOT NULL"),
        ),
    )


class MealRecommendationOperationORM(Base):
    """Append-only replay row for recommendation mutations."""

    __tablename__ = "meal_recommendation_operations"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id = Column(
        String(36),
        ForeignKey("meal_recommendations.id", ondelete="CASCADE"),
        nullable=False,
    )
    slot_id = Column(String(36), nullable=False)
    operation_type = Column(String(30), nullable=False)
    request_id = Column(String(160), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    result_selection_version = Column(Integer, nullable=True)
    result_catalog_meal_id = Column(
        String(36),
        ForeignKey("meal_catalog.id", ondelete="RESTRICT"),
        nullable=True,
    )
    result_logged_meal_id = Column(
        String(36),
        ForeignKey("meal.meal_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "operation_type IN ('swap', 'log')",
            name="ck_meal_recommendation_operations_type",
        ),
        CheckConstraint(
            "length(request_id) BETWEEN 1 AND 160",
            name="ck_meal_recommendation_operations_request_id",
        ),
        CheckConstraint(
            "length(request_fingerprint) = 64",
            name="ck_meal_recommendation_operations_fingerprint",
        ),
        CheckConstraint(
            "("
            "operation_type = 'swap' AND result_selection_version IS NOT NULL "
            "AND result_catalog_meal_id IS NOT NULL AND result_logged_meal_id IS NULL"
            ") OR ("
            "operation_type = 'log' AND result_logged_meal_id IS NOT NULL "
            "AND result_catalog_meal_id IS NULL"
            ")",
            name="ck_meal_recommendation_operations_payload",
        ),
        UniqueConstraint(
            "user_id",
            "operation_type",
            "request_id",
            name="uq_meal_recommendation_operations_user_type_request",
        ),
        Index(
            "idx_meal_recommendation_operations_batch_slot",
            "batch_id",
            "slot_id",
            "created_at",
        ),
    )

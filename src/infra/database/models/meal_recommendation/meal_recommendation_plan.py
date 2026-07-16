"""Database models for durable meal recommendation plans."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from src.infra.database.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class MealRecommendationPlanORM(Base):
    """Owner-scoped durable three-day recommendation plan."""

    __tablename__ = "meal_recommendation_plans"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    timezone = Column(String(64), nullable=False)
    start_date = Column(Date, nullable=False)
    daily_calories = Column(Integer, nullable=False)
    algorithm_version = Column(String(80), nullable=False)
    catalog_release_id = Column(
        String(36),
        ForeignKey("catalog_releases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    allergy_evaluated = Column(Boolean, nullable=False, default=False)
    operation = Column(String(40), nullable=False)
    idempotency_key = Column(String(160), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    superseded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    slots = relationship(
        "MealRecommendationSlotORM",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="MealRecommendationSlotORM.position",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'superseded', 'failed')",
            name="ck_meal_recommendation_plans_status",
        ),
        CheckConstraint(
            "daily_calories > 0",
            name="ck_meal_recommendation_plans_daily_calories",
        ),
        CheckConstraint(
            "length(idempotency_key) BETWEEN 1 AND 160",
            name="ck_meal_recommendation_plans_idempotency_key",
        ),
        UniqueConstraint(
            "user_id",
            "operation",
            "idempotency_key",
            name="uq_meal_recommendation_plans_user_idempotency",
        ),
        Index("idx_meal_recommendation_plans_user_created", "user_id", "created_at"),
    )


class MealRecommendationSlotORM(Base):
    """Selected recipe slot for a durable recommendation plan."""

    __tablename__ = "meal_recommendation_slots"

    id = Column(String(36), primary_key=True, default=_uuid)
    plan_id = Column(
        String(36),
        ForeignKey("meal_recommendation_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    slot_date = Column(Date, nullable=False)
    day_index = Column(Integer, nullable=False)
    meal_type = Column(String(30), nullable=False)
    recipe_version_id = Column(
        String(36),
        ForeignKey("catalog_recipe_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_calories = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    position = Column(Integer, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    logged_meal_id = Column(String(36), nullable=True)
    logged_at = Column(DateTime(timezone=True), nullable=True)

    plan = relationship("MealRecommendationPlanORM", back_populates="slots")
    alternatives = relationship(
        "MealRecommendationSlotAlternativeORM",
        back_populates="slot",
        cascade="all, delete-orphan",
        order_by="MealRecommendationSlotAlternativeORM.position",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("day_index BETWEEN 0 AND 2", name="ck_meal_rec_slots_day"),
        CheckConstraint("target_calories > 0", name="ck_meal_rec_slots_target"),
        UniqueConstraint(
            "plan_id",
            "slot_date",
            "meal_type",
            name="uq_meal_recommendation_slots_plan_date_type",
        ),
        UniqueConstraint(
            "plan_id",
            "recipe_version_id",
            name="uq_meal_recommendation_slots_unique_recipe",
        ),
        UniqueConstraint(
            "logged_meal_id",
            name="uq_meal_recommendation_slots_logged_meal",
        ),
        Index(
            "idx_meal_recommendation_slots_plan_position",
            "plan_id",
            "position",
        ),
    )


class MealRecommendationSwapORM(Base):
    """Audit row for a committed recommendation slot swap."""

    __tablename__ = "meal_recommendation_swaps"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=False)
    plan_id = Column(
        String(36),
        ForeignKey("meal_recommendation_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    slot_id = Column(
        String(36),
        ForeignKey("meal_recommendation_slots.id", ondelete="CASCADE"),
        nullable=False,
    )
    request_id = Column(String(160), nullable=False)
    expected_version = Column(Integer, nullable=False)
    requested_recipe_version_id = Column(
        String(36),
        ForeignKey("catalog_recipe_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    from_recipe_version_id = Column(
        String(36),
        ForeignKey("catalog_recipe_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    to_recipe_version_id = Column(
        String(36),
        ForeignKey("catalog_recipe_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason = Column(String(40), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "expected_version > 0",
            name="ck_meal_recommendation_swaps_expected_version",
        ),
        CheckConstraint(
            "reason IN ('user_requested', 'alternative_selected')",
            name="ck_meal_recommendation_swaps_reason",
        ),
        UniqueConstraint(
            "user_id",
            "request_id",
            name="uq_meal_recommendation_swaps_user_request",
        ),
        Index("idx_meal_recommendation_swaps_slot_created", "slot_id", "created_at"),
    )


class MealRecommendationInteractionORM(Base):
    """Raw owner-scoped recommendation interaction event."""

    __tablename__ = "meal_recommendation_interactions"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=False)
    plan_id = Column(
        String(36),
        ForeignKey("meal_recommendation_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    slot_id = Column(
        String(36),
        ForeignKey("meal_recommendation_slots.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = Column(String(40), nullable=False)
    request_id = Column(String(160), nullable=True)
    meal_id = Column(String(36), nullable=True)
    recipe_version_id = Column(
        String(36),
        ForeignKey("catalog_recipe_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_metadata = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('swap_selected', 'meal_logged')",
            name="ck_meal_recommendation_interactions_type",
        ),
        UniqueConstraint(
            "slot_id",
            "event_type",
            "request_id",
            name="uq_meal_recommendation_interactions_slot_event_request",
        ),
        Index(
            "idx_meal_recommendation_interactions_plan_created",
            "plan_id",
            "created_at",
        ),
    )


class MealRecommendationSlotAlternativeORM(Base):
    """Alternative recipe for one recommendation slot."""

    __tablename__ = "meal_recommendation_slot_alternatives"

    id = Column(String(36), primary_key=True, default=_uuid)
    slot_id = Column(
        String(36),
        ForeignKey("meal_recommendation_slots.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipe_version_id = Column(
        String(36),
        ForeignKey("catalog_recipe_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_calories = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    position = Column(Integer, nullable=False)

    slot = relationship("MealRecommendationSlotORM", back_populates="alternatives")

    __table_args__ = (
        CheckConstraint(
            "target_calories > 0",
            name="ck_meal_rec_alternatives_target",
        ),
        UniqueConstraint(
            "slot_id",
            "position",
            name="uq_meal_recommendation_alternatives_slot_position",
        ),
        UniqueConstraint(
            "slot_id",
            "recipe_version_id",
            name="uq_meal_recommendation_alternatives_slot_recipe",
        ),
        Index(
            "idx_meal_recommendation_alternatives_slot_position",
            "slot_id",
            "position",
        ),
    )

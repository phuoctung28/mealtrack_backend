"""Hydration log ORM model."""

import sqlalchemy as sa
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Index

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class HydrationLogORM(Base, BaseMixin):
    """Stores per-user hydration log entries."""

    __tablename__ = "hydration_logs"

    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    drink_id = Column(String(50), nullable=False)
    volume_ml = Column(Integer, nullable=False)
    credited_ml = Column(Integer, nullable=False)
    source = Column(String(20), nullable=False)  # "hydration" | "caloric_drink"
    meal_id = Column(
        String(36),
        ForeignKey("meal.meal_id", ondelete="SET NULL"),
        nullable=True,
    )
    logged_at = Column(DateTime(timezone=True), nullable=False)
    is_deleted = Column(
        Boolean, default=False, nullable=False, server_default=sa.text("false")
    )

    __table_args__ = (
        Index("idx_hydration_logs_user_logged", "user_id", "logged_at"),
    )

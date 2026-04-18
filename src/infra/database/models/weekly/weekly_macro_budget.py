"""
Weekly macro budget database model.
"""
from sqlalchemy import Column, String, Date, Float, Integer, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import TimestampMixin


class WeeklyMacroBudgetORM(Base, TimestampMixin):
    """SQLAlchemy model for weekly_macro_budgets table."""

    __tablename__ = 'weekly_macro_budgets'

    # Primary key
    weekly_budget_id = Column(String(36), primary_key=True)

    # User reference
    user_id = Column(String(36), nullable=False, index=True)

    # Week start date (Monday)
    week_start_date = Column(Date, nullable=False)

    # Target values (daily × 7)
    target_calories = Column(Float, nullable=False)
    target_protein = Column(Float, nullable=False)
    target_carbs = Column(Float, nullable=False)
    target_fat = Column(Float, nullable=False)

    # Consumed values
    consumed_calories = Column(Float, default=0.0, nullable=False)
    consumed_protein = Column(Float, default=0.0, nullable=False)
    consumed_carbs = Column(Float, default=0.0, nullable=False)
    consumed_fat = Column(Float, default=0.0, nullable=False)

    # Unique constraint and indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'week_start_date', name='uq_user_week'),
        Index('ix_user_week', 'user_id', 'week_start_date'),
    )

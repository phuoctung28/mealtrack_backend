"""
Weekly macro budget database model.
"""
from sqlalchemy import Column, String, Date, Float, Integer, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import TimestampMixin


class WeeklyMacroBudget(Base, TimestampMixin):
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

    def to_domain(self):
        """Convert DB model to domain model."""
        from src.domain.model.weekly import WeeklyMacroBudget as DomainWeeklyMacroBudget

        return DomainWeeklyMacroBudget(
            weekly_budget_id=self.weekly_budget_id,
            user_id=self.user_id,
            week_start_date=self.week_start_date,
            target_calories=self.target_calories,
            target_protein=self.target_protein,
            target_carbs=self.target_carbs,
            target_fat=self.target_fat,
            consumed_calories=self.consumed_calories,
            consumed_protein=self.consumed_protein,
            consumed_carbs=self.consumed_carbs,
            consumed_fat=self.consumed_fat,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, domain_model):
        """Create DB model from domain model."""
        return cls(
            weekly_budget_id=domain_model.weekly_budget_id,
            user_id=domain_model.user_id,
            week_start_date=domain_model.week_start_date,
            target_calories=domain_model.target_calories,
            target_protein=domain_model.target_protein,
            target_carbs=domain_model.target_carbs,
            target_fat=domain_model.target_fat,
            consumed_calories=domain_model.consumed_calories,
            consumed_protein=domain_model.consumed_protein,
            consumed_carbs=domain_model.consumed_carbs,
            consumed_fat=domain_model.consumed_fat,
            created_at=domain_model.created_at,
            updated_at=domain_model.updated_at,
        )

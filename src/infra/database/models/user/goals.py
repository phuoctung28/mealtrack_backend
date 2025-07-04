"""
User goal model for tracking fitness goals and activity levels.
"""
from sqlalchemy import Column, String, Boolean, Integer, Float, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import SecondaryEntityMixin


class UserGoal(Base, SecondaryEntityMixin):
    """Tracks user fitness goals and activity levels over time."""
    __tablename__ = 'user_goals'
    
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    activity_level = Column(String(30), nullable=False)  # sedentary, light, moderate, active, extra
    fitness_goal = Column(String(30), nullable=False)  # maintenance, cutting, bulking
    target_weight_kg = Column(Float, nullable=True)
    meals_per_day = Column(Integer, default=3, nullable=False)
    snacks_per_day = Column(Integer, default=1, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('target_weight_kg IS NULL OR target_weight_kg > 0', name='check_target_weight_positive'),
        CheckConstraint('meals_per_day >= 1 AND meals_per_day <= 10', name='check_meals_per_day_range'),
        CheckConstraint('snacks_per_day >= 0 AND snacks_per_day <= 10', name='check_snacks_per_day_range'),
        Index('idx_user_goal_current', 'user_id', 'is_current'),
    )
    
    # Relationships
    user = relationship("User", back_populates="goals")
    tdee_calculations = relationship("TdeeCalculation", back_populates="goal")
"""
Meal plan day model for individual days within a meal plan.
"""
from sqlalchemy import Column, String, Date, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import SecondaryEntityMixin


class MealPlanDay(Base, SecondaryEntityMixin):
    """Represents a single day within a meal plan."""
    __tablename__ = "meal_plan_days"
    
    meal_plan_id = Column(String(36), ForeignKey("meal_plans.id"), nullable=False)
    date = Column(Date, nullable=False)
    
    # Relationships
    meal_plan = relationship("MealPlan", back_populates="days")
    meals = relationship("PlannedMeal", back_populates="day", cascade="all, delete-orphan")
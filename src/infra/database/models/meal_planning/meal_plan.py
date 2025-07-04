"""
Meal plan model for storing user meal planning preferences and settings.
"""
from sqlalchemy import Column, String, Integer, JSON, Enum
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin
from src.infra.database.models.enums import FitnessGoalEnum, PlanDurationEnum


class MealPlan(Base, BaseMixin):
    """Main meal plan entity storing user preferences and settings."""
    __tablename__ = "meal_plans"
    
    user_id = Column(String(255), nullable=False, index=True)
    
    # User preferences stored as JSON
    dietary_preferences = Column(JSON)
    allergies = Column(JSON)
    fitness_goal = Column(Enum(FitnessGoalEnum))
    meals_per_day = Column(Integer)
    snacks_per_day = Column(Integer)
    cooking_time_weekday = Column(Integer)
    cooking_time_weekend = Column(Integer)
    favorite_cuisines = Column(JSON)
    disliked_ingredients = Column(JSON)
    plan_duration = Column(Enum(PlanDurationEnum))
    
    # Relationships
    days = relationship("MealPlanDay", back_populates="meal_plan", cascade="all, delete-orphan")
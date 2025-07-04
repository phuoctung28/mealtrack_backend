"""
Planned meal model for individual meals within a meal plan day.
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, JSON, Enum, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import SecondaryEntityMixin
from src.infra.database.models.enums import MealTypeEnum


class PlannedMeal(Base, SecondaryEntityMixin):
    """Represents a planned meal within a meal plan day."""
    __tablename__ = "planned_meals"
    
    day_id = Column(Integer, ForeignKey("meal_plan_days.id"), nullable=False)
    meal_type = Column(Enum(MealTypeEnum), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    prep_time = Column(Integer)  # minutes
    cook_time = Column(Integer)  # minutes
    
    # Nutrition info
    calories = Column(Integer)
    protein = Column(Float)
    carbs = Column(Float)
    fat = Column(Float)
    
    # Stored as JSON arrays
    ingredients = Column(JSON)
    instructions = Column(JSON)
    
    # Dietary flags
    is_vegetarian = Column(Boolean, default=False)
    is_vegan = Column(Boolean, default=False)
    is_gluten_free = Column(Boolean, default=False)
    
    cuisine_type = Column(String(100))
    
    # Relationships
    day = relationship("MealPlanDay", back_populates="meals")
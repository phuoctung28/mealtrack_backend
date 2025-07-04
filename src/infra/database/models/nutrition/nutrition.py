"""
Nutrition model for overall nutritional information of a meal.
"""
from sqlalchemy import Column, Float, Text, String, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import SecondaryEntityMixin
from .macros import Macros


class Nutrition(Base, SecondaryEntityMixin):
    """Database model for nutrition data."""
    
    calories = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=True)
    raw_ai_response = Column(Text, nullable=True)
    
    # Relationships
    macros = relationship("Macros", 
                         uselist=False, 
                         foreign_keys=[Macros.nutrition_id], 
                         cascade="all, delete-orphan")
    food_items = relationship("FoodItem", 
                             back_populates="nutrition", 
                             cascade="all, delete-orphan")
    meal_id = Column(String(36), ForeignKey("meal.meal_id"), nullable=False)
    meal = relationship("Meal", back_populates="nutrition")
    
    def to_domain(self):
        """Convert DB model to domain model."""
        from src.domain.model.nutrition import Nutrition as DomainNutrition
        
        # Convert food items if they exist
        food_items = [item.to_domain() for item in self.food_items] if self.food_items else None
        
        return DomainNutrition(
            calories=self.calories,
            macros=self.macros.to_domain() if self.macros else None,
            micros=None,  # Not implemented yet
            food_items=food_items,
            confidence_score=self.confidence_score
        )
    
    @classmethod
    def from_domain(cls, domain_model, meal_id):
        """Create DB model from domain model."""
        nutrition = cls(
            calories=domain_model.calories,
            confidence_score=domain_model.confidence_score,
            meal_id=meal_id
        )
        
        # Add macros if they exist
        if domain_model.macros:
            # nutrition_id will be available after flush
            nutrition.macros = Macros.from_domain(domain_model.macros)
            
        # Add food items if they exist
        if domain_model.food_items:
            from .food_item import FoodItem
            # nutrition_id will be available after flush
            nutrition.food_items = [
                FoodItem.from_domain(food_item)
                for food_item in domain_model.food_items
            ]
            
        return nutrition
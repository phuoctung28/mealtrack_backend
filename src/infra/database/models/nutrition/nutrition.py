"""
Nutrition model for overall nutritional information of a meal.
"""
from sqlalchemy import Column, Float, Text, String, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import SecondaryEntityMixin


class Nutrition(Base, SecondaryEntityMixin):
    """Database model for nutrition data."""
    
    calories = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=True)
    raw_ai_response = Column(Text, nullable=True)
    
    # Macro fields (previously in separate Macros table)
    protein = Column(Float, default=0, nullable=False)
    carbs = Column(Float, default=0, nullable=False)
    fat = Column(Float, default=0, nullable=False)
    
    # Relationships
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
        
        # Create macros domain object from our fields
        from src.domain.model.nutrition import Macros as DomainMacros
        macros = DomainMacros(
            protein=self.protein,
            carbs=self.carbs,
            fat=self.fat,
        )
        
        return DomainNutrition(
            calories=self.calories,
            macros=macros,
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
        
        # Set macro fields directly
        if domain_model.macros:
            nutrition.protein = domain_model.macros.protein
            nutrition.carbs = domain_model.macros.carbs
            nutrition.fat = domain_model.macros.fat
            
        # Add food items if they exist
        if domain_model.food_items:
            from .food_item import FoodItem
            # nutrition_id will be available after flush
            nutrition.food_items = [
                FoodItem.from_domain(food_item)
                for food_item in domain_model.food_items
            ]
            
        return nutrition
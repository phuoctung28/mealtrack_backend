"""
Nutrition model for overall nutritional information of a meal.
"""
from sqlalchemy import Column, Float, Text, String, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import SecondaryEntityMixin


class Nutrition(Base, SecondaryEntityMixin):
    """Database model for nutrition data."""

    confidence_score = Column(Float, nullable=True)
    raw_ai_response = Column(Text, nullable=True)

    # Macro fields — calories are always derived: P*4 + (C-fiber)*4 + fiber*2 + F*9
    protein = Column(Float, default=0, nullable=False)
    carbs = Column(Float, default=0, nullable=False)
    fat = Column(Float, default=0, nullable=False)
    fiber = Column(Float, default=0, nullable=False)
    sugar = Column(Float, default=0, nullable=False)

    # Relationships
    food_items = relationship("FoodItem",
                             back_populates="nutrition",
                             cascade="all, delete-orphan",
                             order_by="FoodItem.order_index")
    meal_id = Column(String(36), ForeignKey("meal.meal_id"), nullable=False)
    meal = relationship("Meal", back_populates="nutrition")

    def to_domain(self):
        """Convert DB model to domain model."""
        from src.domain.model.nutrition import Nutrition as DomainNutrition
        from src.domain.model.nutrition import Macros as DomainMacros

        food_items = [item.to_domain() for item in self.food_items] if self.food_items else None

        macros = DomainMacros(
            protein=self.protein,
            carbs=self.carbs,
            fat=self.fat,
            fiber=self.fiber or 0.0,
            sugar=self.sugar or 0.0,
        )

        return DomainNutrition(
            macros=macros,
            micros=None,  # Not implemented yet
            food_items=food_items,
            confidence_score=self.confidence_score
        )

    @classmethod
    def from_domain(cls, domain_model, meal_id):
        """Create DB model from domain model."""
        meal_id_str = str(meal_id) if meal_id else None

        nutrition = cls(
            confidence_score=domain_model.confidence_score,
            meal_id=meal_id_str
        )

        if domain_model.macros:
            nutrition.protein = domain_model.macros.protein
            nutrition.carbs = domain_model.macros.carbs
            nutrition.fat = domain_model.macros.fat
            nutrition.fiber = domain_model.macros.fiber
            nutrition.sugar = domain_model.macros.sugar

        if domain_model.food_items:
            from .food_item import FoodItem
            food_items = []
            for idx, food_item in enumerate(domain_model.food_items):
                db_item = FoodItem.from_domain(food_item)
                db_item.order_index = idx
                food_items.append(db_item)
            nutrition.food_items = food_items

        return nutrition

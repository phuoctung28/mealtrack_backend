"""
Macronutrient model for storing protein, carbs, fat, and fiber data.
"""
from sqlalchemy import Column, Float, Integer, ForeignKey

from src.infra.database.config import Base
from src.infra.database.models.base import SecondaryEntityMixin


class Macros(Base, SecondaryEntityMixin):
    """Database model for macronutrients."""
    
    __tablename__ = "macros"
    
    # id is inherited from SecondaryEntityMixin as Integer primary key
    protein = Column(Float, default=0)
    carbs = Column(Float, default=0)
    fat = Column(Float, default=0)
    fiber = Column(Float, nullable=True)
    
    # Relationships - can belong to either Nutrition OR FoodItem
    nutrition_id = Column(Integer, ForeignKey("nutrition.id"), nullable=True)
    food_item_id = Column(Integer, ForeignKey("fooditem.id"), nullable=True)
    
    def to_domain(self):
        """Convert DB model to domain model."""
        from src.domain.model.macros import Macros as DomainMacros
        
        return DomainMacros(
            protein=self.protein,
            carbs=self.carbs,
            fat=self.fat,
            fiber=self.fiber
        )
    
    @classmethod
    def from_domain(cls, domain_model, nutrition_id=None, food_item_id=None):
        """Create DB model from domain model."""
        return cls(
            protein=domain_model.protein,
            carbs=domain_model.carbs,
            fat=domain_model.fat,
            fiber=domain_model.fiber,
            nutrition_id=nutrition_id,
            food_item_id=food_item_id
        )
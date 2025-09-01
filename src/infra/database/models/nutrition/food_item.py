"""
Food item model for individual food components within a meal.
"""
from sqlalchemy import Column, String, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import SecondaryEntityMixin


class FoodItem(Base, SecondaryEntityMixin):
    """Database model for food items in a meal."""
    
    __tablename__ = 'food_item'  # Explicit table name to match migration
    
    name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    calories = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    
    # Macro fields (previously in separate Macros table)
    protein = Column(Float, default=0, nullable=False)
    carbs = Column(Float, default=0, nullable=False)
    fat = Column(Float, default=0, nullable=False)
    fiber = Column(Float, nullable=True)
    
    # Foreign keys
    nutrition_id = Column(Integer, ForeignKey("nutrition.id"), nullable=False)
    
    # Relationships
    nutrition = relationship("Nutrition", back_populates="food_items")
    
    def to_domain(self):
        """Convert DB model to domain model."""
        from src.domain.model.nutrition import FoodItem as DomainFoodItem
        
        # Create macros domain object from our fields
        from src.domain.model.nutrition import Macros as DomainMacros
        macros = DomainMacros(
            protein=self.protein,
            carbs=self.carbs,
            fat=self.fat,
            fiber=self.fiber
        )
        
        return DomainFoodItem(
            name=self.name,
            quantity=self.quantity,
            unit=self.unit,
            calories=self.calories,
            macros=macros,
            micros=None,  # Not implemented yet
            confidence=self.confidence
        )
    
    @classmethod
    def from_domain(cls, domain_model, nutrition_id=None):
        """Create DB model from domain model."""
        item = cls(
            name=domain_model.name,
            quantity=domain_model.quantity,
            unit=domain_model.unit,
            calories=domain_model.calories,
            confidence=domain_model.confidence,
            nutrition_id=nutrition_id
        )
        
        # Set macro fields directly
        if domain_model.macros:
            item.protein = domain_model.macros.protein
            item.carbs = domain_model.macros.carbs
            item.fat = domain_model.macros.fat
            item.fiber = domain_model.macros.fiber
            
        return item
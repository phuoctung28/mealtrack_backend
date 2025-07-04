"""
Food item model for individual food components within a meal.
"""
from sqlalchemy import Column, String, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import SecondaryEntityMixin
from .macros import Macros


class FoodItem(Base, SecondaryEntityMixin):
    """Database model for food items in a meal."""
    
    name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    calories = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    
    # Foreign keys
    nutrition_id = Column(Integer, ForeignKey("nutrition.id"), nullable=False)
    
    # Relationships
    nutrition = relationship("Nutrition", back_populates="food_items")
    macros = relationship("Macros", uselist=False, cascade="all, delete-orphan")
    
    def to_domain(self):
        """Convert DB model to domain model."""
        from src.domain.model.nutrition import FoodItem as DomainFoodItem
        
        return DomainFoodItem(
            name=self.name,
            quantity=self.quantity,
            unit=self.unit,
            calories=self.calories,
            macros=self.macros.to_domain() if self.macros else None,
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
        
        if domain_model.macros:
            # food_item_id will be available after flush
            item.macros = Macros.from_domain(domain_model.macros)
            
        return item
"""
Food item model for individual food components within a meal.
"""
from sqlalchemy import Column, String, Float, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import PrimaryEntityMixin


class FoodItem(Base, PrimaryEntityMixin):
    """Database model for food items in a meal."""
    
    __tablename__ = 'food_item'  # Explicit table name to match migration
    
    name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    calories = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    
    # Edit support fields  
    fdc_id = Column(Integer, nullable=True)  # USDA FDC ID if available
    is_custom = Column(Boolean, default=False, nullable=False)  # Whether this is a custom ingredient
    
    # Macro fields (previously in separate Macros table)
    protein = Column(Float, default=0, nullable=False)
    carbs = Column(Float, default=0, nullable=False)
    fat = Column(Float, default=0, nullable=False)
    
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
        )
        
        return DomainFoodItem(
            id=self.id,  # Both database and domain use UUID strings now
            name=self.name,
            quantity=self.quantity,
            unit=self.unit,
            calories=self.calories,
            macros=macros,
            micros=None,  # Not implemented yet
            confidence=self.confidence,
            fdc_id=self.fdc_id,
            is_custom=self.is_custom
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
            nutrition_id=nutrition_id,
            fdc_id=getattr(domain_model, 'fdc_id', None),
            is_custom=getattr(domain_model, 'is_custom', False)
        )
        
        # Set the ID if provided (for updates)
        if hasattr(domain_model, 'id') and domain_model.id:
            item.id = domain_model.id
        
        # Set macro fields directly
        if domain_model.macros:
            item.protein = domain_model.macros.protein
            item.carbs = domain_model.macros.carbs
            item.fat = domain_model.macros.fat
            
        return item
from sqlalchemy import Column, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class Macros(Base):
    """Database model for macronutrients."""
    
    __tablename__ = "macros"
    
    id = Column(String(36), primary_key=True)
    protein = Column(Float, default=0)
    carbs = Column(Float, default=0)
    fat = Column(Float, default=0)
    fiber = Column(Float, nullable=True)
    
    # Relationships
    nutrition_id = Column(String(36), ForeignKey("nutrition.id"), nullable=True)
    food_item_id = Column(String(36), ForeignKey("fooditem.id"), nullable=True)
    
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
        """Create DB model from src.domain model."""
        import uuid
        
        return cls(
            id=str(uuid.uuid4()),
            protein=domain_model.protein,
            carbs=domain_model.carbs,
            fat=domain_model.fat,
            fiber=domain_model.fiber,
            nutrition_id=nutrition_id,
            food_item_id=food_item_id
        )

class FoodItem(Base, BaseMixin):
    """Database model for food items in a meal."""
    
    name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    calories = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    
    # Foreign keys
    nutrition_id = Column(String(36), ForeignKey("nutrition.id"), nullable=False)
    
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
    def from_domain(cls, domain_model, nutrition_id):
        """Create DB model from src.domain model."""
        import uuid
        
        food_item_id = str(uuid.uuid4())
        item = cls(
            id=food_item_id,
            name=domain_model.name,
            quantity=domain_model.quantity,
            unit=domain_model.unit,
            calories=domain_model.calories,
            confidence=domain_model.confidence,
            nutrition_id=nutrition_id
        )
        
        if domain_model.macros:
            item.macros = Macros.from_domain(domain_model.macros, food_item_id=food_item_id)
            
        return item

class Nutrition(Base, BaseMixin):
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
        """Create DB model from src.domain model."""
        import uuid
        
        nutrition_id = str(uuid.uuid4())
        nutrition = cls(
            id=nutrition_id,
            calories=domain_model.calories,
            confidence_score=domain_model.confidence_score,
            meal_id=meal_id
        )
        
        # Add macros if they exist
        if domain_model.macros:
            nutrition.macros = Macros.from_domain(domain_model.macros, nutrition_id=nutrition_id)
            
        # Add food items if they exist
        if domain_model.food_items:
            nutrition.food_items = [
                FoodItem.from_domain(food_item, nutrition_id=nutrition_id)
                for food_item in domain_model.food_items
            ]
            
        return nutrition 
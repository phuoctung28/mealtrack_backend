import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..nutrition import Macros, Micros
from src.domain.services.timezone_utils import utc_now


@dataclass
class Ingredient:
    """
    Domain model representing an ingredient that belongs to a food item.
    """
    ingredient_id: str
    food_id: str  # Reference to the parent food
    name: str
    quantity: float
    unit: str
    calories: Optional[float] = None
    macros: Optional[Macros] = None
    micros: Optional[Micros] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate invariants."""
        # Validate UUID formats
        try:
            uuid.UUID(self.ingredient_id)
            uuid.UUID(self.food_id)
        except ValueError as e:
            raise ValueError(f"Invalid UUID format: {e}")
        
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be positive: {self.quantity}")
            
        if self.calories is not None and self.calories < 0:
            raise ValueError(f"Calories cannot be negative: {self.calories}")
    
    @classmethod
    def create_new(cls, food_id: str, name: str, quantity: float, unit: str, **kwargs) -> 'Ingredient':
        """Factory method to create a new ingredient."""
        return cls(
            ingredient_id=str(uuid.uuid4()),
            food_id=food_id,
            name=name,
            quantity=quantity,
            unit=unit,
            created_at=utc_now(),
            **kwargs
        )
    
    def update_nutritional_info(self, calories: Optional[float], macros: Optional[Macros], micros: Optional[Micros] = None) -> 'Ingredient':
        """Update the nutritional information of the ingredient."""
        return Ingredient(
            ingredient_id=self.ingredient_id,
            food_id=self.food_id,
            name=self.name,
            quantity=self.quantity,
            unit=self.unit,
            calories=calories,
            macros=macros,
            micros=micros,
            created_at=self.created_at,
            updated_at=utc_now()
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        result = {
            "ingredient_id": self.ingredient_id,
            "food_id": self.food_id,
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit
        }
        
        if self.calories is not None:
            result["calories"] = self.calories
        if self.macros:
            result["macros"] = self.macros.to_dict()
        if self.micros:
            result["micros"] = self.micros.to_dict()
        if self.created_at:
            result["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            result["updated_at"] = self.updated_at.isoformat()
            
        return result 
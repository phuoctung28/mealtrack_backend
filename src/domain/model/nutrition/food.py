import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .macros import Macros
from src.domain.services.timezone_utils import utc_now


@dataclass
class Food:
    """
    Domain model representing a food item in the database.
    """
    food_id: str
    name: str
    brand: Optional[str] = None
    description: Optional[str] = None
    serving_size: Optional[float] = None
    serving_unit: Optional[str] = None
    calories_per_serving: Optional[float] = None
    macros_per_serving: Optional[Macros] = None
    barcode: Optional[str] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_verified: bool = False
    
    def __post_init__(self):
        """Validate invariants."""
        # Validate UUID format
        try:
            uuid.UUID(self.food_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for food_id: {self.food_id}")
        
        if self.serving_size is not None and self.serving_size <= 0:
            raise ValueError(f"Serving size must be positive: {self.serving_size}")
            
        if self.calories_per_serving is not None and self.calories_per_serving < 0:
            raise ValueError(f"Calories cannot be negative: {self.calories_per_serving}")
    
    @classmethod
    def create_new(cls, name: str, **kwargs) -> 'Food':
        """Factory method to create a new food item."""
        return cls(
            food_id=str(uuid.uuid4()),
            name=name,
            created_at=utc_now(),
            **kwargs
        )
    
    def update_nutritional_info(self, calories: float, macros: Macros) -> 'Food':
        """Update the nutritional information of the food."""
        return Food(
            food_id=self.food_id,
            name=self.name,
            brand=self.brand,
            description=self.description,
            serving_size=self.serving_size,
            serving_unit=self.serving_unit,
            calories_per_serving=calories,
            macros_per_serving=macros,
            barcode=self.barcode,
            image_url=self.image_url,
            created_at=self.created_at,
            updated_at=utc_now(),
            is_verified=self.is_verified
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        result = {
            "food_id": self.food_id,
            "name": self.name,
            "is_verified": self.is_verified
        }
        
        if self.brand:
            result["brand"] = self.brand
        if self.description:
            result["description"] = self.description
        if self.serving_size:
            result["serving_size"] = self.serving_size
        if self.serving_unit:
            result["serving_unit"] = self.serving_unit
        if self.calories_per_serving:
            result["calories_per_serving"] = self.calories_per_serving
        if self.macros_per_serving:
            result["macros_per_serving"] = self.macros_per_serving.to_dict()
        if self.barcode:
            result["barcode"] = self.barcode
        if self.image_url:
            result["image_url"] = self.image_url
        if self.created_at:
            result["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            result["updated_at"] = self.updated_at.isoformat()
            
        return result 
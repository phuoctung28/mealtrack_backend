from dataclasses import dataclass
from typing import Dict, List, Optional

from .macros import Macros
from .micros import Micros


@dataclass
class FoodItem:
    """Represents a single food item in a meal with nutritional information."""
    id: str
    name: str
    quantity: float
    unit: str
    calories: float
    macros: Macros
    micros: Optional[Micros] = None
    confidence: float = 1.0  # 0.0-1.0 confidence score from AI or lookup
    fdc_id: Optional[int] = None  # USDA FDC ID if available
    is_custom: bool = False  # Whether this is a custom ingredient
    
    def __post_init__(self):
        """Validate invariants."""
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be positive: {self.quantity}")
        if self.calories < 0:
            raise ValueError(f"Calories cannot be negative: {self.calories}")
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1: {self.confidence}")

    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
        result = {
            "id": self.id,
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "calories": self.calories,
            "macros": self.macros.to_dict(),
            "confidence": self.confidence,
            "is_custom": self.is_custom
        }
        if self.micros:
            result["micros"] = self.micros.to_dict()
        if self.fdc_id:
            result["fdc_id"] = self.fdc_id
        return result

@dataclass
class Nutrition:
    """Value object representing full nutritional information for a meal."""
    calories: float
    macros: Macros
    micros: Optional[Micros] = None
    food_items: Optional[List[FoodItem]] = None
    confidence_score: float = 1.0  # 0.0-1.0 overall confidence score
    
    def __post_init__(self):
        """Validate invariants."""
        if self.calories < 0:
            raise ValueError(f"Calories cannot be negative: {self.calories}")
        if not 0 <= self.confidence_score <= 1:
            raise ValueError(f"Confidence score must be between 0 and 1: {self.confidence_score}")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
        result = {
            "calories": self.calories,
            "macros": self.macros.to_dict(),
            "confidence_score": self.confidence_score
        }
        
        if self.micros:
            result["micros"] = self.micros.to_dict()
            
        if self.food_items:
            result["food_items"] = [item.to_dict() for item in self.food_items]
            
        return result 
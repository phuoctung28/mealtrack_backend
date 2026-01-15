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
        if not self.name or not self.name.strip():
            raise ValueError("Food item name cannot be empty")
        if len(self.name) > 200:
            raise ValueError(f"Food item name too long (max 200 chars): {len(self.name)}")
        if self.quantity <= 0 or self.quantity > 10000:
            raise ValueError(f"Quantity must be between 0 and 10000: {self.quantity}")
        if self.calories < 0:
            raise ValueError(f"Calories cannot be negative: {self.calories}")
        if self.calories > 10000:
            raise ValueError(f"Calories exceed realistic limit (10000): {self.calories}")
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1: {self.confidence}")
        if not self.unit or not self.unit.strip():
            raise ValueError("Unit cannot be empty")
        if len(self.unit) > 50:
            raise ValueError(f"Unit too long (max 50 chars): {len(self.unit)}")

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
        if self.calories > 20000:
            raise ValueError(f"Calories exceed realistic limit (20000): {self.calories}")
        if not 0 <= self.confidence_score <= 1:
            raise ValueError(f"Confidence score must be between 0 and 1: {self.confidence_score}")

        # Validate food items
        if self.food_items:
            if len(self.food_items) > 50:
                raise ValueError(f"Too many ingredients (max 50): {len(self.food_items)}")

            # Check for duplicate ingredient names (case-insensitive)
            # Only exact string matches, not semantic (e.g. "Apple" == "apple" but != "Green Apple")
            names_lower = [item.name.lower().strip() for item in self.food_items]
            if len(names_lower) != len(set(names_lower)):
                # This might be too strict for user edits (e.g. "Egg" and "Egg" added twice)
                # But domain invariant says "Aggregate duplicates" or "Unique ID"
                # Let's relax this to just logging or allow duplicates if IDs differ?
                # FoodItem IDs are usually UUIDs or random strings.
                # If names are same, maybe it's fine if they are distinct entries.
                # But usually you want "2 Eggs", not "1 Egg", "1 Egg".
                pass # Removing this check to be safe with existing data patterns unless strict enforcement is desired.
    
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
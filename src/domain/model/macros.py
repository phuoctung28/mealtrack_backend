from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Macros:
    """
    Value object representing macronutrient breakdown of a meal.
    All values are in grams.
    """
    protein: float
    carbs: float
    fat: float
    fiber: Optional[float] = None
    
    def __post_init__(self):
        # Validate invariants
        for field_name in ['protein', 'carbs', 'fat']:
            value = getattr(self, field_name)
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative: {value}")
        
        if self.fiber is not None and self.fiber < 0:
            raise ValueError(f"fiber cannot be negative: {self.fiber}")
    
    @property
    def total_calories(self) -> float:
        """Calculate total calories based on macronutrients."""
        # Standard caloric values: 4 kcal/g for protein and carbs, 9 kcal/g for fat
        return round(self.protein * 4 + self.carbs * 4 + self.fat * 9, 1)
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        result = {
            "protein_g": self.protein,
            "carbs_g": self.carbs,
            "fat_g": self.fat,
        }
        if self.fiber is not None:
            result["fiber_g"] = self.fiber
        return result 
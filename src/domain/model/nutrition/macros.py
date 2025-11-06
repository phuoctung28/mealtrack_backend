from dataclasses import dataclass


@dataclass
class Macros:
    """
    Value object representing macronutrient breakdown of a meal.
    All values are in grams.
    """
    protein: float
    carbs: float
    fat: float
    
    def __post_init__(self):
        # Validate invariants
        for field_name in ['protein', 'carbs', 'fat']:
            value = getattr(self, field_name)
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative: {value}")
    
    @property
    def total_calories(self) -> float:
        """Calculate total calories based on macronutrients."""
        # Standard caloric values: 4 cal/g for protein and carbs, 9 cal/g for fat
        return round(self.protein * 4 + self.carbs * 4 + self.fat * 9, 1)
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        result = {
            "protein_g": self.protein,
            "carbs_g": self.carbs,
            "fat_g": self.fat,
        }
        return result 
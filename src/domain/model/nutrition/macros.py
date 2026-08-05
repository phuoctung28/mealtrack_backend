from dataclasses import dataclass


@dataclass
class Macros:
    """
    Value object representing macronutrient breakdown of a meal.
    All values are in grams.
    Values may be manually overridden by the user, so they are intentionally
    not constrained here.
    """

    protein: float
    carbs: float
    fat: float
    fiber: float = 0.0
    sugar: float = 0.0

    @property
    def total_calories(self) -> float:
        """Derive calories: P*4 + (C-fiber)*4 + fiber*2 + F*9."""
        net_carbs = max(0.0, self.carbs - self.fiber)
        return round(
            self.protein * 4 + net_carbs * 4 + self.fiber * 2 + self.fat * 9,
            1,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "protein_g": self.protein,
            "carbs_g": self.carbs,
            "fat_g": self.fat,
            "fiber_g": self.fiber,
            "sugar_g": self.sugar,
        }

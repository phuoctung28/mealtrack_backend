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

    @staticmethod
    def raw_total_calories(
        protein: float, carbs: float, fat: float, fiber: float = 0.0
    ) -> float:
        """Canonical unrounded formula: P*4 + max(C-fiber,0)*4 + fiber*2 + F*9.

        Sole Python source of truth for the calorie arithmetic. Never rounds
        — callers apply their own existing rounding precision so routing a
        call site through this method never changes that site's output.
        """
        net_carbs = max(0.0, carbs - fiber)
        return protein * 4 + net_carbs * 4 + fiber * 2 + fat * 9

    @property
    def total_calories(self) -> float:
        """Derive calories: P*4 + (C-fiber)*4 + fiber*2 + F*9."""
        return round(
            Macros.raw_total_calories(self.protein, self.carbs, self.fat, self.fiber),
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

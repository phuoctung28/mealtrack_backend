"""
Rule-based nutrition description service.

Given macro values, produces a human-readable sentence like:
  "This meal is high in protein (40g), moderate in carbs (30g), and low in fat (8g)
   with 350 kcal. Excellent for muscle building and recovery."
"""
from typing import Optional


class NutritionDescriptionService:
    """Generates human-readable nutrition descriptions from macro values."""

    # Percentage-of-caloric-contribution thresholds
    _PROTEIN_THRESHOLDS = (20.0, 35.0)   # (low->moderate, moderate->high)
    _CARBS_THRESHOLDS = (30.0, 50.0)
    _FAT_THRESHOLDS = (25.0, 40.0)

    def describe(
        self,
        calories: int,
        protein: float,
        carbs: float,
        fat: float,
    ) -> str:
        """
        Build a nutrition description from macro values.

        Args:
            calories: Total kilocalories.
            protein: Protein in grams.
            carbs: Carbohydrates in grams.
            fat: Fat in grams.

        Returns:
            A 2-sentence natural-language description.
        """
        macro_calories = protein * 4 + carbs * 4 + fat * 9
        if macro_calories < 1:
            return "Nutritional information is not available for this meal."

        protein_pct = (protein * 4) / macro_calories * 100
        carbs_pct = (carbs * 4) / macro_calories * 100
        fat_pct = (fat * 9) / macro_calories * 100

        protein_level = self._level(protein_pct, self._PROTEIN_THRESHOLDS)
        carbs_level = self._level(carbs_pct, self._CARBS_THRESHOLDS)
        fat_level = self._level(fat_pct, self._FAT_THRESHOLDS)

        first_sentence = (
            f"This meal is {protein_level} in protein ({protein:.0f}g), "
            f"{carbs_level} in carbs ({carbs:.0f}g), and "
            f"{fat_level} in fat ({fat:.0f}g) with {calories} kcal."
        )

        context = self._context_sentence(protein_level, carbs_level, fat_level, calories)
        return f"{first_sentence} {context}"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _level(pct: float, thresholds: tuple) -> str:
        low_boundary, high_boundary = thresholds
        if pct < low_boundary:
            return "low"
        if pct < high_boundary:
            return "moderate"
        return "high"

    @staticmethod
    def _context_sentence(
        protein_level: str,
        carbs_level: str,
        fat_level: str,
        calories: int,
    ) -> str:
        if calories > 800:
            return "A hearty, energy-dense meal — ideal for high-activity days."
        if protein_level == "high" and fat_level in ("low", "moderate"):
            return "Excellent for muscle building and recovery."
        if fat_level == "high" and carbs_level == "low":
            return "A keto-friendly option rich in healthy fats."
        if carbs_level == "high" and protein_level in ("low", "moderate"):
            return "Great for sustained energy and fueling activity."
        return "A well-balanced meal for everyday nutrition."

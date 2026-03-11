"""
Post-generation validation for AI-generated macros.
Ensures P*4 + (C-fiber)*4 + fiber*2 + F*9 ≈ reported calories.
"""
import logging

logger = logging.getLogger(__name__)


class MacroValidationService:
    """Validate and correct AI-generated macros after generation."""

    # Max acceptable divergence between derived and reported calories
    CALORIE_DIFF_THRESHOLD_PCT = 10.0

    def validate_and_correct(self, macros: dict) -> dict:
        """Verify P*4 + C*4 + F*9 ≈ reported calories. Correct if off.

        Args:
            macros: Dict with calories, protein, carbs, fat keys.

        Returns:
            Corrected macros dict. Adds _validation metadata if corrected.
        """
        protein = max(0.0, macros.get("protein", 0.0))
        carbs = max(0.0, macros.get("carbs", 0.0))
        fat = max(0.0, macros.get("fat", 0.0))
        fiber = max(0.0, macros.get("fiber", 0.0))
        reported_cal = macros.get("calories", 0.0)

        # Fiber-aware: net_carb*4 + fiber*2 + P*4 + F*9
        net_carbs = max(0.0, carbs - fiber)
        derived_cal = round(protein * 4 + net_carbs * 4 + fiber * 2 + fat * 9, 1)

        # Clamp negatives
        macros["protein"] = protein
        macros["carbs"] = carbs
        macros["fat"] = fat
        macros["fiber"] = fiber

        if reported_cal and reported_cal > 0:
            diff_pct = abs(derived_cal - reported_cal) / reported_cal * 100
            if diff_pct > self.CALORIE_DIFF_THRESHOLD_PCT:
                # Trust macros over reported calories
                logger.warning(
                    "Macro validation corrected calories: %s → %s (%.1f%% off)",
                    reported_cal,
                    derived_cal,
                    diff_pct,
                )
                macros["calories"] = derived_cal
                macros["_validation"] = {
                    "corrected": True,
                    "original_calories": reported_cal,
                    "diff_pct": round(diff_pct, 1),
                }
                return macros

        # No correction needed — still derive from macros for consistency
        macros["calories"] = derived_cal
        return macros

"""Service for calculating meal portion sizes based on user profile."""

from src.domain.model.meal_suggestion.portion_target import PortionTarget


class PortionCalculationService:
    """Calculate target calories based on meal type and user profile.

    All calculations are percentage-based from user's daily TDEE:
    - Snack: 10-15% of daily target (default 12%)
    - Main: ~33% of daily target (one of ~3 meals/day)
    - OMAD: 100% of daily target
    """

    # Percentage-based constants
    SNACK_MIN_PERCENT = 0.10  # 10% of daily
    SNACK_MAX_PERCENT = 0.15  # 15% of daily
    SNACK_DEFAULT_PERCENT = 0.12  # 12% of daily (midpoint)

    MAIN_MEAL_PERCENT = 0.33  # ~33% of daily (1/3)
    MAIN_VARIANCE_PERCENT = 0.15  # ±15% variance

    OMAD_PERCENT = 1.0  # 100% of daily
    OMAD_VARIANCE_PERCENT = 0.10  # ±10% variance

    def calculate_snack_target(self, daily_target: int) -> PortionTarget:
        """Snack = 10-15% of daily target."""
        target = int(daily_target * self.SNACK_DEFAULT_PERCENT)
        min_cal = int(daily_target * self.SNACK_MIN_PERCENT)
        max_cal = int(daily_target * self.SNACK_MAX_PERCENT)

        return PortionTarget(
            target_calories=target,
            min_calories=min_cal,
            max_calories=max_cal,
            meals_per_day=0,  # N/A for snacks
        )

    def calculate_main_meal_target(
        self, daily_target: int, meals_per_day: int = 3
    ) -> PortionTarget:
        """Main meal = ~33% of daily target (±15% variance)."""
        target = int(daily_target * self.MAIN_MEAL_PERCENT)
        variance = int(target * self.MAIN_VARIANCE_PERCENT)

        return PortionTarget(
            target_calories=target,
            min_calories=target - variance,
            max_calories=target + variance,
            meals_per_day=meals_per_day,
        )

    def calculate_omad_target(self, daily_target: int) -> PortionTarget:
        """OMAD = 100% of daily target (±10% variance)."""
        target = int(daily_target * self.OMAD_PERCENT)
        variance = int(target * self.OMAD_VARIANCE_PERCENT)

        return PortionTarget(
            target_calories=target,
            min_calories=target - variance,
            max_calories=target + variance,
            meals_per_day=1,
        )

    def get_target_for_meal_type(
        self, meal_type: str, daily_target: int, meals_per_day: int = 3
    ) -> PortionTarget:
        """Get portion target based on meal type (percentage-based)."""
        if meal_type == "snack":
            return self.calculate_snack_target(daily_target)
        elif meal_type == "main":
            return self.calculate_main_meal_target(daily_target, meals_per_day)
        elif meal_type == "omad":
            return self.calculate_omad_target(daily_target)
        else:
            # Fallback to main meal
            return self.calculate_main_meal_target(daily_target, meals_per_day)

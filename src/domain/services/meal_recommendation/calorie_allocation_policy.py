"""Deterministic calorie allocation for three daily recommendation slots."""

from __future__ import annotations

MEAL_TYPE_ORDER = ("breakfast", "lunch", "dinner")
_MEAL_WEIGHTS = {
    "breakfast": 0.25,
    "lunch": 0.375,
    "dinner": 0.375,
}


class CalorieAllocationPolicy:
    """Allocate daily calories across supported meal slots deterministically."""

    def allocate(self, daily_calories: int) -> dict[str, int]:
        if daily_calories <= 0:
            raise ValueError("daily_calories must be positive")

        allocations = {
            meal_type: round(daily_calories * weight)
            for meal_type, weight in _MEAL_WEIGHTS.items()
        }
        drift = daily_calories - sum(allocations.values())
        allocations["dinner"] += drift
        return {meal_type: allocations[meal_type] for meal_type in MEAL_TYPE_ORDER}

    def target_for(self, daily_calories: int, meal_type: str) -> int:
        """Return the browse target for a supported meal type."""
        if meal_type == "snack":
            if daily_calories <= 0:
                raise ValueError("daily_calories must be positive")
            return max(1, round(daily_calories * 0.10))
        allocations = self.allocate(daily_calories)
        try:
            return allocations[meal_type]
        except KeyError:
            raise ValueError(f"unsupported meal_type: {meal_type}") from None

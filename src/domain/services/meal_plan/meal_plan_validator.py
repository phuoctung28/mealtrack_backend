"""Meal plan validation logic."""
from dataclasses import dataclass
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validation operation."""
    is_valid: bool
    errors: List[str]


class MealPlanValidator:
    """Validates meal plan requests and responses."""

    def validate_weekly_response(self, data: Dict[str, Any], request: Dict[str, Any]) -> ValidationResult:
        """Validate weekly response structure."""
        errors = []

        week_data = data.get("week", [])
        if len(week_data) != 7:
            errors.append(f"Expected 7 days, got {len(week_data)}")

        required_fields = {
            "meal_type", "name", "calories", "protein", "carbs", "fat",
            "ingredients", "seasonings", "instructions", "is_vegetarian",
            "is_vegan", "is_gluten_free", "cuisine_type"
        }

        include_snacks = request.get("include_snacks", False)
        expected_meals_per_day = 3 + (1 if include_snacks else 0)

        for day in week_data:
            day_name = day.get("day", "")
            meals = day.get("meals", [])

            if len(meals) < expected_meals_per_day:
                logger.warning(f"{day_name}: Expected {expected_meals_per_day} meals, got {len(meals)}")

            for meal in meals:
                missing_fields = required_fields - meal.keys()
                if missing_fields:
                    logger.warning(f"{day_name} meal missing fields: {missing_fields}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

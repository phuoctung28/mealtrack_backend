"""Meal plan formatting and response building logic."""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.domain.model.meal_planning import MealGenerationRequest
from src.domain.services.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class MealPlanFormatter:
    """Formats meal plans for API responses."""

    def flatten_week(self, week_block: List[Dict]) -> List[Dict]:
        """Flatten week structure to meal list."""
        meals = []
        for day in week_block:
            for meal in day["meals"]:
                meals.append({"day": day["day"], **meal})
        return meals

    def format_weekly_response(self, meals: List[Dict], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format weekly response structure."""
        # Use provided start/end dates if available, otherwise calculate current week
        if "start_date_obj" in request_data and "end_date_obj" in request_data:
            start_date = request_data["start_date_obj"]
            end_date = request_data["end_date_obj"]
        else:
            # Fallback to current week calculation
            today = utc_now().date()
            days_since_monday = today.weekday()  # Monday = 0
            start_date = today - timedelta(days=days_since_monday)
            end_date = start_date + timedelta(days=6)

        # Create day name to date mapping
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_to_date = {}
        for i, day_name in enumerate(day_names):
            day_date = start_date + timedelta(days=i)
            day_to_date[day_name] = day_date

        # Ensure all meals have required dietary fields and add dates
        for meal in meals:
            meal.setdefault("is_vegetarian", False)
            meal.setdefault("is_vegan", False)
            meal.setdefault("is_gluten_free", False)
            meal.setdefault("cuisine_type", "International")
            meal.setdefault("seasonings", ["salt", "pepper"])  # Default seasonings if missing

            # Add actual date and formatted day string
            if meal["day"] in day_to_date:
                meal_date = day_to_date[meal["day"]]
                meal["date"] = meal_date.isoformat()
                meal["day_formatted"] = f"{meal['day']}, {meal_date.strftime('%B %d, %Y')}"
            else:
                # Fallback for unknown day names
                meal["date"] = start_date.isoformat()
                meal["day_formatted"] = meal["day"]

        total_cals = sum(m["calories"] for m in meals)
        total_prot = sum(m["protein"] for m in meals)
        total_carbs = sum(m["carbs"] for m in meals)
        total_fat = sum(m["fat"] for m in meals)

        # Group by day name - schema expects each day to map directly to a list of meals
        grouped = {}
        for m in meals:
            day_name = m["day"]
            if day_name not in grouped:
                grouped[day_name] = []
            grouped[day_name].append(m)

        return {
            "user_id": request_data.get("user_id", "unknown"),
            "plan_type": "weekly",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": grouped,
            "meals": meals,
            "total_nutrition": {
                "calories": total_cals,
                "protein": round(total_prot, 1),
                "carbs": round(total_carbs, 1),
                "fat": round(total_fat, 1),
            },
            "daily_average_nutrition": {
                "calories": total_cals // 7,
                "protein": round(total_prot / 7, 1),
                "carbs": round(total_carbs / 7, 1),
                "fat": round(total_fat / 7, 1),
            },
            "target_nutrition": {
                "calories": request_data.get("target_calories", 1800),
                "protein": request_data.get("target_protein", 120.0),
                "carbs": request_data.get("target_carbs", 200.0),
                "fat": request_data.get("target_fat", 80.0),
            },
            "user_preferences": {
                "dietary_preferences": request_data.get("dietary_preferences", []),
                "health_conditions": request_data.get("health_conditions", []),
                "allergies": request_data.get("allergies", []),
                "activity_level": request_data.get("activity_level", "moderate"),
                "fitness_goal": request_data.get("fitness_goal", "maintenance"),
                "meals_per_day": request_data.get("meals_per_day", 3),
                "snacks_per_day": 1 if request_data.get("include_snacks", False) else 0,
            },
        }

    def calculate_nutrition_totals(self, meals: List[Dict]) -> Dict[str, float]:
        """Helper method to calculate nutrition totals from meals."""
        return {
            "calories": sum(meal["calories"] for meal in meals),
            "protein": sum(meal["protein"] for meal in meals),
            "carbs": sum(meal["carbs"] for meal in meals),
            "fat": sum(meal["fat"] for meal in meals)
        }

    def validate_and_adjust_weekly_nutrition(
        self,
        meals: List[Dict],
        generation_request: MealGenerationRequest
    ) -> List[Dict]:
        """Validate and adjust weekly nutrition to match targets."""
        target_nutrition = generation_request.nutrition_targets
        expected_weekly_totals = {
            "calories": target_nutrition.calories * 7,
            "protein": target_nutrition.protein * 7,
            "carbs": target_nutrition.carbs * 7,
            "fat": target_nutrition.fat * 7
        }

        # Calculate current totals using helper method
        current_totals = self.calculate_nutrition_totals(meals)

        # Check if adjustment is needed (allow 5% tolerance)
        tolerance = 0.05
        needs_adjustment = any(
            abs(current_totals[nutrient] - expected_weekly_totals[nutrient]) > expected_weekly_totals[nutrient] * tolerance
            for nutrient in expected_weekly_totals
        )

        if not needs_adjustment:
            logger.info("Weekly nutrition targets are within acceptable range")
            return meals

        logger.warning(f"Weekly nutrition adjustment needed. Current: {current_totals}")
        logger.warning(f"Expected: {expected_weekly_totals}")

        # Calculate adjustment factors
        adjustment_factors = {
            nutrient: expected_weekly_totals[nutrient] / current_totals[nutrient] if current_totals[nutrient] > 0 else 1
            for nutrient in expected_weekly_totals
        }

        # Apply adjustments proportionally
        adjusted_meals = []
        for meal in meals:
            adjusted_meal = meal.copy()
            adjusted_meal["calories"] = int(meal["calories"] * adjustment_factors["calories"])
            adjusted_meal["protein"] = round(meal["protein"] * adjustment_factors["protein"], 1)
            adjusted_meal["carbs"] = round(meal["carbs"] * adjustment_factors["carbs"], 1)
            adjusted_meal["fat"] = round(meal["fat"] * adjustment_factors["fat"], 1)
            adjusted_meals.append(adjusted_meal)

        # Verify final totals using helper method
        final_totals = self.calculate_nutrition_totals(adjusted_meals)
        logger.info(f"Adjusted weekly nutrition: {final_totals}")

        return adjusted_meals

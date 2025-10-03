"""
GetDailyActivitiesQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any

from src.app.events.base import EventHandler, handles
from src.app.queries.activity import GetDailyActivitiesQuery
from src.domain.model.meal import MealStatus
from src.domain.ports.meal_repository_port import MealRepositoryPort

logger = logging.getLogger(__name__)


@handles(GetDailyActivitiesQuery)
class GetDailyActivitiesQueryHandler(EventHandler[GetDailyActivitiesQuery, List[Dict[str, Any]]]):
    """Handler for getting daily activities (meals and workouts)."""

    def __init__(self, meal_repository: MealRepositoryPort = None):
        self.meal_repository = meal_repository

    def set_dependencies(self, meal_repository: MealRepositoryPort):
        """Set dependencies for dependency injection."""
        self.meal_repository = meal_repository

    async def handle(self, query: GetDailyActivitiesQuery) -> List[Dict[str, Any]]:
        """Get all activities for the specified date."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")

        activities = []

        # Get meal activities
        meal_activities = self._get_meal_activities(query.target_date, query.user_id)
        logger.info(f"Found {len(meal_activities)} meal activities for user {query.user_id} on date {query.target_date.strftime('%Y-%m-%d')}")
        activities.extend(meal_activities)

        # Get workout activities (placeholder for now)
        workout_activities = self._get_workout_activities(query.target_date, query.user_id)
        logger.info(f"Found {len(workout_activities)} workout activities for user {query.user_id} on date {query.target_date.strftime('%Y-%m-%d')}")
        activities.extend(workout_activities)

        # Sort by timestamp (newest first)
        activities.sort(key=lambda x: x['timestamp'], reverse=True)

        logger.info(f"Retrieved {len(activities)} total activities")
        return activities

    def _get_meal_activities(self, target_date: datetime, user_id: str) -> List[Dict[str, Any]]:
        """Get meal activities for a specific date and user."""
        try:
            date_obj = target_date.date()
            meals = self.meal_repository.find_by_date(date_obj, user_id=user_id)

            meal_activities = []
            for meal in meals:
                # Only include meals with nutrition data and exclude INACTIVE
                if not meal.nutrition or meal.status not in [MealStatus.READY, MealStatus.ENRICHING]:
                    continue
                if meal.status == MealStatus.INACTIVE:
                    continue

                # Build activity from meal
                activity = self._build_meal_activity(meal, target_date)
                meal_activities.append(activity)

            return meal_activities

        except Exception as e:
            logger.error(f"Error getting meal activities: {str(e)}", exc_info=True)
            return []

    def _build_meal_activity(self, meal, target_date: datetime) -> Dict[str, Any]:
        """Build activity dictionary from meal."""
        # Determine meal type based on time
        meal_type = self._determine_meal_type(meal.created_at)

        # Estimate weight
        estimated_weight = self._estimate_meal_weight(meal)

        # Get image URL
        image_url = None
        if hasattr(meal, 'image') and meal.image:
            image_url = meal.image.url

        # Build activity
        return {
            "id": meal.meal_id,
            "type": "meal",
            "timestamp": meal.created_at.isoformat() if meal.created_at else target_date.isoformat(),
            "title": meal.dish_name or "Unknown Meal",
            "meal_type": meal_type,
            "calories": round(meal.nutrition.calories, 1) if meal.nutrition else 0,
            "macros": {
                "protein": round(meal.nutrition.macros.protein, 1) if meal.nutrition else 0,
                "carbs": round(meal.nutrition.macros.carbs, 1) if meal.nutrition else 0,
                "fat": round(meal.nutrition.macros.fat, 1) if meal.nutrition else 0,
            },
            "quantity": estimated_weight,
            "status": meal.status.value if meal.status else "unknown",
            "image_url": image_url
        }

    def _estimate_meal_weight(self, meal) -> float:
        """Estimate meal weight from nutrition data."""
        # Default weight
        estimated_weight = 300.0

        # Check if meal has updated weight
        if hasattr(meal, 'weight_grams'):
            return meal.weight_grams

        # Try to get from food items
        if meal.nutrition and meal.nutrition.food_items:
            first_food = meal.nutrition.food_items[0]
            if first_food.unit and 'g' in first_food.unit.lower():
                estimated_weight = first_food.quantity
            elif first_food.quantity > 10:  # Assume grams if quantity is large
                estimated_weight = first_food.quantity

        return estimated_weight

    def _get_workout_activities(self, target_date: datetime, user_id: str) -> List[Dict[str, Any]]:
        """Get workout activities for a specific date and user."""
        # TODO: When workout service is implemented, fetch from there
        # For now, return empty list
        return []

    def _determine_meal_type(self, meal_time: datetime) -> str:
        """Determine meal type based on time of day."""
        if not meal_time:
            return "snack"

        hour = meal_time.hour
        if 5 <= hour < 11:
            return "breakfast"
        elif 11 <= hour < 16:
            return "lunch"
        elif 16 <= hour < 22:
            return "dinner"
        else:
            return "snack"

"""
ReplaceMealInPlanCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any

from src.app.commands.meal_plan import ReplaceMealInPlanCommand
from src.app.events.base import EventHandler, handles
from src.domain.services.meal_plan_orchestration_service import MealPlanOrchestrationService
from src.infra.adapters.meal_generation_service import MealGenerationService

logger = logging.getLogger(__name__)


@handles(ReplaceMealInPlanCommand)
class ReplaceMealInPlanCommandHandler(EventHandler[ReplaceMealInPlanCommand, Dict[str, Any]]):
    """Handler for replacing meals in plans."""

    def __init__(self, orchestration_service: MealPlanOrchestrationService = None):
        if orchestration_service:
            self.orchestration_service = orchestration_service
        else:
            # Fallback to default instantiation for backward compatibility
            meal_generation_service = MealGenerationService()
            self.orchestration_service = MealPlanOrchestrationService(meal_generation_service)
        # In-memory storage for demo purposes
        self._meal_plans: Dict[str, Dict[str, Any]] = {}

    def set_dependencies(self, orchestration_service: MealPlanOrchestrationService = None):
        """Set dependencies for dependency injection."""
        if orchestration_service:
            self.orchestration_service = orchestration_service

    async def handle(self, command: ReplaceMealInPlanCommand) -> Dict[str, Any]:
        """Replace a meal in a meal plan."""
        # For demo purposes, create a simple replacement
        # In production, this would fetch from database
        raise ValueError(f"Meal plan {command.plan_id} not found - feature not fully implemented")

        # Find and replace the meal
        old_meal = None
        for day in meal_plan["days"]:
            if day["date"] == command.date:
                for i, meal in enumerate(day["meals"]):
                    if meal["meal_id"] == command.meal_id:
                        old_meal = meal

                        # Generate replacement meal
                        preferences = {
                            "meal_type": meal["meal_type"],
                            "dietary_preferences": command.dietary_preferences or [],
                            "exclude_ingredients": command.exclude_ingredients or [],
                            "preferred_cuisine": command.preferred_cuisine
                        }

                        # Get user preferences from meal plan
                        user_data = meal_plan.get("user_data", {})
                        new_meal = self.suggestion_service.generate_single_meal(
                            user_data=user_data,
                            meal_type=meal["meal_type"],
                            additional_preferences=preferences
                        )

                        # Replace in the plan
                        day["meals"][i] = self._format_meal(new_meal)

                        from src.app.events.meal_plan import MealReplacedEvent
                        result = {
                            "new_meal": day["meals"][i],
                            "events": [
                                MealReplacedEvent(
                                    aggregate_id=command.plan_id,
                                    plan_id=command.plan_id,
                                    old_meal_id=command.meal_id,
                                    new_meal_id=new_meal.id,
                                    date=command.date
                                )
                            ]
                        }

                        logger.info(f"Replaced meal {command.meal_id} with {new_meal.id} in plan {command.plan_id}")
                        return result

        raise ValueError(f"Meal {command.meal_id} not found in plan {command.plan_id} for date {command.date}")

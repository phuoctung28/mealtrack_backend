"""
GetMealPlanQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.queries.meal_plan import GetMealPlanQuery

logger = logging.getLogger(__name__)


@handles(GetMealPlanQuery)
class GetMealPlanQueryHandler(EventHandler[GetMealPlanQuery, Dict[str, Any]]):
    """Handler for getting meal plans."""

    def __init__(self):
        # In-memory storage for demo
        self._meal_plans: Dict[str, Dict[str, Any]] = {}

    def set_dependencies(self):
        """No external dependencies needed."""
        pass

    async def handle(self, query: GetMealPlanQuery) -> Dict[str, Any]:
        """Get a meal plan by ID."""
        # For demo purposes, return not found
        # In production, this would fetch from database
        raise ResourceNotFoundException(
            message="Meal plan not found",
            details={"plan_id": query.plan_id}
        )

        return {
            "meal_plan": meal_plan
        }

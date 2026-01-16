"""
GetMealPlanQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.queries.meal_plan import GetMealPlanQuery
from src.infra.database.models.meal_planning.meal_plan import MealPlan as DBMealPlan
from src.infra.database.models.meal_planning.meal_plan_day import MealPlanDay as DBMealPlanDay
from src.infra.database.models.meal_planning.planned_meal import PlannedMeal as DBPlannedMeal
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(GetMealPlanQuery)
class GetMealPlanQueryHandler(EventHandler[GetMealPlanQuery, Dict[str, Any]]):
    """Handler for getting meal plans."""

    def __init__(self):
        pass

    def set_dependencies(self):
        """No external dependencies needed."""
        pass

    async def handle(self, query: GetMealPlanQuery) -> Dict[str, Any]:
        """Get a meal plan by ID."""
        with UnitOfWork() as uow:
            db = uow.session
            
            # Find meal plan
            meal_plan = db.query(DBMealPlan).filter(DBMealPlan.id == query.plan_id).first()
            if not meal_plan:
                raise ResourceNotFoundException(
                    message="Meal plan not found",
                    details={"plan_id": query.plan_id}
                )
            
            # Get all days for this plan
            days = db.query(DBMealPlanDay).filter(
                DBMealPlanDay.meal_plan_id == meal_plan.id
            ).all()
            
            # Build response
            meals_by_date = {}
            for day in days:
                planned_meals = db.query(DBPlannedMeal).filter(
                    DBPlannedMeal.day_id == day.id
                ).all()
                
                meals_by_date[str(day.date)] = [
                    {
                        "planned_meal_id": str(pm.id),
                        "name": pm.name,
                        "meal_type": pm.meal_type.value,
                        "calories": pm.calories,
                        "protein": pm.protein,
                        "carbs": pm.carbs,
                        "fat": pm.fat,
                    }
                    for pm in planned_meals
                ]
            
            return {
                "meal_plan": {
                    "plan_id": meal_plan.id,
                    "user_id": meal_plan.user_id,
                    "meals": meals_by_date
                }
            }

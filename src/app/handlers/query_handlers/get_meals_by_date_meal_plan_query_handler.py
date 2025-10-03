"""
GetMealsByDateQueryHandler (Meal Plan) - Individual handler file.
Auto-extracted for better maintainability.

Note: This is the meal plan version, different from the meal query version.
"""
import logging
from typing import Dict, Any

from src.app.events.base import EventHandler, handles
from src.app.queries.meal_plan import GetMealsByDateQuery
from src.domain.model.meal_plan import PlannedMeal, MealType
from src.domain.model.meal_query_response import MealsForDateResponse

logger = logging.getLogger(__name__)


@handles(GetMealsByDateQuery)
class GetMealsByDateQueryHandler(EventHandler[GetMealsByDateQuery, Dict[str, Any]]):
    """Handler for getting meals by specific date."""

    def __init__(self, db=None):
        self.db = db

    def set_dependencies(self, db=None):
        """Set database dependency if available."""
        self.db = db

    async def handle(self, query: GetMealsByDateQuery) -> Dict[str, Any]:
        """Get meals for a specific date."""
        try:
            if self.db:
                # Query database for meals on the specific date
                from src.infra.database.models.meal_planning.meal_plan import MealPlan as DBMealPlan
                from src.infra.database.models.meal_planning.meal_plan_day import MealPlanDay
                from src.infra.database.models.meal_planning.planned_meal import PlannedMeal as DBPlannedMeal

                # Find meal plan days that match the user and date
                meal_plan_days = self.db.query(MealPlanDay).join(DBMealPlan).filter(
                    DBMealPlan.user_id == query.user_id,
                    MealPlanDay.date == query.meal_date
                ).all()

                # Get all planned meals for those days and convert to domain models
                domain_meals = []
                for day in meal_plan_days:
                    db_planned_meals = self.db.query(DBPlannedMeal).filter(
                        DBPlannedMeal.day_id == day.id
                    ).all()

                    # Convert database models to domain models
                    for db_meal in db_planned_meals:
                        domain_meal = self._convert_db_meal_to_domain(db_meal)
                        domain_meals.append(domain_meal)

                # Create response using domain model
                response = MealsForDateResponse(
                    date=query.meal_date,
                    day_formatted=query.meal_date.strftime("%A, %B %d, %Y"),
                    meals=domain_meals,
                    total_meals=len(domain_meals),
                    user_id=query.user_id
                )

                return response.to_dict()

            # Fallback: return empty response when no database
            response = MealsForDateResponse.empty_response(query.user_id, query.meal_date)
            return response.to_dict()

        except Exception as e:
            logger.error(f"Error getting meals for date {query.meal_date}: {str(e)}")
            # Return empty results instead of failing
            response = MealsForDateResponse.empty_response(query.user_id, query.meal_date)
            return response.to_dict()

    def _convert_db_meal_to_domain(self, db_meal) -> PlannedMeal:
        """Convert database PlannedMeal model to domain PlannedMeal model."""
        return PlannedMeal(
            meal_id=str(db_meal.id),
            meal_type=MealType(db_meal.meal_type.value) if db_meal.meal_type else MealType.BREAKFAST,
            name=db_meal.name,
            description=db_meal.description or "",
            prep_time=db_meal.prep_time or 0,
            cook_time=db_meal.cook_time or 0,
            calories=db_meal.calories or 0,
            protein=db_meal.protein or 0.0,
            carbs=db_meal.carbs or 0.0,
            fat=db_meal.fat or 0.0,
            ingredients=db_meal.ingredients or [],
            seasonings=db_meal.seasonings or [],
            instructions=db_meal.instructions or [],
            is_vegetarian=db_meal.is_vegetarian or False,
            is_vegan=db_meal.is_vegan or False,
            is_gluten_free=db_meal.is_gluten_free or False,
            cuisine_type=db_meal.cuisine_type
        )

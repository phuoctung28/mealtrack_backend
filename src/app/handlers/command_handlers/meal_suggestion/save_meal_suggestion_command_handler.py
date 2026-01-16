"""
SaveMealSuggestionCommandHandler - Handler for saving meal suggestions to planned_meals.
"""
import logging
from datetime import datetime
from uuid import uuid4

from src.app.commands.meal_suggestion import SaveMealSuggestionCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.uow import UnitOfWork
from src.infra.database.models.enums import MealTypeEnum
from src.infra.database.models.meal_planning.meal_plan import MealPlan as DBMealPlan
from src.infra.database.models.meal_planning.meal_plan_day import MealPlanDay as DBMealPlanDay
from src.infra.database.models.meal_planning.planned_meal import PlannedMeal as DBPlannedMeal

logger = logging.getLogger(__name__)


@handles(SaveMealSuggestionCommand)
class SaveMealSuggestionCommandHandler(
    EventHandler[SaveMealSuggestionCommand, str]
):
    """Handler for saving meal suggestions to planned_meals table."""

    async def handle(self, command: SaveMealSuggestionCommand) -> str:
        """
        Save meal suggestion to planned_meals table.
        
        Creates MealPlan and MealPlanDay if they don't exist for the user and date.
        
        Args:
            command: SaveMealSuggestionCommand with meal suggestion data
            
        Returns:
            planned_meal_id: ID of the created planned meal
        """
        with UnitOfWork() as uow:
            db = uow.session

            # Parse meal_date
            meal_date = datetime.strptime(command.meal_date, "%Y-%m-%d").date()
            
            # Find or create MealPlan for user
            meal_plan = db.query(DBMealPlan).filter(
                DBMealPlan.user_id == command.user_id
            ).first()
            
            if not meal_plan:
                # Create a minimal meal plan if none exists
                meal_plan = DBMealPlan(
                    id=str(uuid4()),
                    user_id=command.user_id,
                    dietary_preferences=[],
                    allergies=[],
                    meals_per_day=3,
                    snacks_per_day=1,
                    cooking_time_weekday=30,
                    cooking_time_weekend=45,
                    favorite_cuisines=[],
                    disliked_ingredients=[],
                    plan_duration=None,  # Can be set later
                )
                db.add(meal_plan)
                db.flush()
                logger.info(f"Created new MealPlan {meal_plan.id} for user {command.user_id}")
            
            # Find or create MealPlanDay for target date
            meal_plan_day = db.query(DBMealPlanDay).filter(
                DBMealPlanDay.meal_plan_id == meal_plan.id,
                DBMealPlanDay.date == meal_date
            ).first()
            
            if not meal_plan_day:
                # Create meal plan day if it doesn't exist
                meal_plan_day = DBMealPlanDay(
                    meal_plan_id=meal_plan.id,
                    date=meal_date
                )
                db.add(meal_plan_day)
                db.flush()
                logger.info(f"Created new MealPlanDay for date {meal_date} in plan {meal_plan.id}")
            
            # Create PlannedMeal
            planned_meal = DBPlannedMeal(
                day_id=meal_plan_day.id,
                meal_type=MealTypeEnum(command.meal_type),
                name=command.name,
                description=command.description,
                prep_time=None,  # Not provided in suggestion
                cook_time=command.estimated_cook_time_minutes,
                calories=command.calories,
                protein=command.protein,
                carbs=command.carbs,
                fat=command.fat,
                ingredients=command.ingredients_list,
                seasonings=[],  # Not provided in suggestion
                instructions=command.instructions,
                is_vegetarian=False,  # Could be inferred from ingredients, but not provided
                is_vegan=False,
                is_gluten_free=False,
                cuisine_type=None,
            )
            db.add(planned_meal)
            db.flush()  # Flush to get the ID
            uow.commit()  # Commit the transaction
            # Refresh after commit to ensure we have the latest state
            db.refresh(planned_meal)
            
            logger.info(
                f"Saved meal suggestion {command.suggestion_id} as planned_meal {planned_meal.id} "
                f"for user {command.user_id} on {meal_date}"
            )
            
            return str(planned_meal.id)

        # Any exceptions will cause UnitOfWork.__exit__ to roll back the transaction

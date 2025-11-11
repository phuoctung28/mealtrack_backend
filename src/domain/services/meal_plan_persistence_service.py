"""
Shared meal plan persistence service.
Handles conversion between domain models and ORM models.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.domain.model.meal_planning import UserPreferences
from src.infra.database.models.enums import (
    FitnessGoalEnum,
    PlanDurationEnum,
    MealTypeEnum,
)
from src.infra.database.models.meal_planning import (
    MealPlan as MealPlanORM,
    MealPlanDay as MealPlanDayORM,
    PlannedMeal as PlannedMealORM,
)

logger = logging.getLogger(__name__)


class MealPlanPersistenceService:
    """Shared service for meal plan persistence operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def save_daily_meal_plan(self, meal_plan_data: Dict[str, Any], user_preferences: UserPreferences, user_id: str) -> str:
        """Save a daily meal plan and return the plan ID."""
        try:
            # Convert domain enums to database enums
            fitness_goal_orm = FitnessGoalEnum(user_preferences.fitness_goal.value)
            plan_duration_orm = PlanDurationEnum(user_preferences.plan_duration.value)
            
            # Create ORM meal plan
            meal_plan_orm = MealPlanORM(
                user_id=user_id,
                dietary_preferences=[pref.value for pref in user_preferences.dietary_preferences],
                allergies=user_preferences.allergies,
                fitness_goal=fitness_goal_orm,
                meals_per_day=user_preferences.meals_per_day,
                snacks_per_day=user_preferences.snacks_per_day,
                cooking_time_weekday=user_preferences.cooking_time_weekday,
                cooking_time_weekend=user_preferences.cooking_time_weekend,
                favorite_cuisines=user_preferences.favorite_cuisines,
                disliked_ingredients=user_preferences.disliked_ingredients,
                plan_duration=plan_duration_orm,
            )
            self.db.add(meal_plan_orm)
            self.db.flush()  # Get the meal plan ID
            
            # Create day plan for today
            day_plan_orm = MealPlanDayORM(
                meal_plan_id=meal_plan_orm.id,
                date=datetime.now().date()
            )
            self.db.add(day_plan_orm)
            self.db.flush()
            
            # Create planned meals
            for meal_data in meal_plan_data.get('meals', []):
                meal_orm_data = self._meal_dict_to_orm_data(meal_data)
                meal_orm = PlannedMealORM(
                    day_id=day_plan_orm.id,
                    **meal_orm_data
                )
                self.db.add(meal_orm)
            
            self.db.commit()
            return str(meal_plan_orm.id)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save daily meal plan: {e}")
            raise
    
    def save_weekly_meal_plan(self, plan_json: Dict[str, Any], user_preferences: UserPreferences, user_id: str) -> str:
        """Save a weekly meal plan and return the plan ID."""
        try:
            # Convert domain enums to database enums
            fitness_goal_orm = FitnessGoalEnum(user_preferences.fitness_goal.value)
            plan_duration_orm = PlanDurationEnum(user_preferences.plan_duration.value)
            
            # Create ORM meal plan
            meal_plan_orm = MealPlanORM(
                user_id=user_id,
                dietary_preferences=[pref.value for pref in user_preferences.dietary_preferences],
                allergies=user_preferences.allergies,
                fitness_goal=fitness_goal_orm,
                meals_per_day=user_preferences.meals_per_day,
                snacks_per_day=user_preferences.snacks_per_day,
                cooking_time_weekday=user_preferences.cooking_time_weekday,
                cooking_time_weekend=user_preferences.cooking_time_weekend,
                favorite_cuisines=user_preferences.favorite_cuisines,
                disliked_ingredients=user_preferences.disliked_ingredients,
                plan_duration=plan_duration_orm,
            )
            self.db.add(meal_plan_orm)
            self.db.flush()
            
            # Create day plans for the week
            today = datetime.now().date()
            weekday_index = {
                "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6,
            }
            
            for day_name, day_data in plan_json["days"].items():
                offset = weekday_index[day_name.lower()]
                day_date = today + timedelta(days=offset)
                
                # Create ORM MealPlanDay
                day_plan_orm = MealPlanDayORM(
                    meal_plan_id=meal_plan_orm.id,
                    date=day_date
                )
                self.db.add(day_plan_orm)
                self.db.flush()
                
                # Create planned meals for this day
                # day_data is now a list of meals directly (matching schema)
                meals_list = day_data if isinstance(day_data, list) else []
                for meal_json in meals_list:
                    meal_orm_data = self._meal_dict_to_orm_data(meal_json)
                    meal_orm = PlannedMealORM(
                        day_id=day_plan_orm.id,
                        **meal_orm_data
                    )
                    self.db.add(meal_orm)
            
            self.db.commit()
            return str(meal_plan_orm.id)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save weekly meal plan: {e}")
            raise
    
    def _meal_dict_to_orm_data(self, meal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert meal dictionary to ORM PlannedMeal data."""
        try:
            meal_type = MealTypeEnum(meal_data["meal_type"].lower())
        except (KeyError, ValueError):
            logger.warning("Unknown or missing meal_type – defaulting to breakfast")
            meal_type = MealTypeEnum.breakfast

        return {
            "meal_type": meal_type,
            "name": meal_data.get("name", "Unnamed meal"),
            "description": meal_data.get("description", ""),
            "prep_time": meal_data.get("prep_time", 0),
            "cook_time": meal_data.get("cook_time", 0),
            "calories": meal_data.get("calories", 0),
            "protein": meal_data.get("protein", 0.0),
            "carbs": meal_data.get("carbs", 0.0),
            "fat": meal_data.get("fat", 0.0),
            "ingredients": meal_data.get("ingredients", []),
            "seasonings": meal_data.get("seasonings", []),
            "instructions": meal_data.get("instructions", []),
            "is_vegetarian": meal_data.get("is_vegetarian", False),
            "is_vegan": meal_data.get("is_vegan", False),
            "is_gluten_free": meal_data.get("is_gluten_free", False),
            "cuisine_type": meal_data.get("cuisine_type", "International"),
        }
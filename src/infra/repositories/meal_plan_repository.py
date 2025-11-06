"""
Meal Plan Repository for persisting meal plans.
"""

from typing import Optional

from sqlalchemy.orm import Session

from src.domain.model.meal_planning import MealPlan
from src.infra.database.config import SessionLocal
from src.infra.database.models.enums import FitnessGoalEnum, PlanDurationEnum, MealTypeEnum
from src.infra.database.models.meal_planning.meal_plan import MealPlan as DBMealPlan
from src.infra.database.models.meal_planning.meal_plan_day import MealPlanDay as DBMealPlanDay
from src.infra.database.models.meal_planning.planned_meal import PlannedMeal as DBPlannedMeal


class MealPlanRepository:
    """Repository for meal plan persistence operations."""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def _get_db(self):
        if self.db:
            return self.db
        else:
            return SessionLocal()
    
    def _close_db_if_created(self, db):
        if self.db is None and db is not None:
            db.close()
    
    def save(self, meal_plan: MealPlan) -> MealPlan:
        """Save a meal plan to the database."""
        db = self._get_db()
        
        try:
            # Create DB MealPlan
            db_meal_plan = DBMealPlan(
                id=meal_plan.plan_id,
                user_id=meal_plan.user_id,
                dietary_preferences=[pref.value for pref in meal_plan.preferences.dietary_preferences],
                allergies=meal_plan.preferences.allergies,
                fitness_goal=FitnessGoalEnum(meal_plan.preferences.fitness_goal.value),
                meals_per_day=meal_plan.preferences.meals_per_day,
                snacks_per_day=meal_plan.preferences.snacks_per_day,
                cooking_time_weekday=meal_plan.preferences.cooking_time_weekday,
                cooking_time_weekend=meal_plan.preferences.cooking_time_weekend,
                favorite_cuisines=meal_plan.preferences.favorite_cuisines,
                disliked_ingredients=meal_plan.preferences.disliked_ingredients,
                plan_duration=PlanDurationEnum(meal_plan.preferences.plan_duration.value)
            )
            db.add(db_meal_plan)
            
            # Create days and meals
            for day in meal_plan.days:
                db_day = DBMealPlanDay(
                    meal_plan_id=db_meal_plan.id,
                    date=day.date
                )
                db.add(db_day)
                
                for meal in day.meals:
                    db_meal = DBPlannedMeal(
                        day_id=db_day.id,
                        meal_type=MealTypeEnum(meal.meal_type.value),
                        name=meal.name,
                        description=meal.description,
                        prep_time=meal.prep_time,
                        cook_time=meal.cook_time,
                        calories=meal.calories,
                        protein=meal.protein,
                        carbs=meal.carbs,
                        fat=meal.fat,
                        ingredients=meal.ingredients,
                        instructions=meal.instructions,
                        is_vegetarian=meal.is_vegetarian,
                        is_vegan=meal.is_vegan,
                        is_gluten_free=meal.is_gluten_free,
                        cuisine_type=meal.cuisine_type
                    )
                    db.add(db_meal)
            
            db.commit()
            db.refresh(db_meal_plan)
            return meal_plan
        except Exception as e:
            db.rollback()
            raise e
        finally:
            self._close_db_if_created(db)
    
    def find_by_id(self, plan_id: str) -> Optional[MealPlan]:
        """Find a meal plan by ID."""
        db = self._get_db()
        
        try:
            db_plan = db.query(DBMealPlan).filter(DBMealPlan.id == plan_id).first()
            if db_plan:
                # TODO: Map back to domain model - for now return the DB model
                return db_plan
            return None
        finally:
            self._close_db_if_created(db) 
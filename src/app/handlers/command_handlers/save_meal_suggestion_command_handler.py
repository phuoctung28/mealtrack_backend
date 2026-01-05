"""
SaveMealSuggestionCommandHandler - Handler for saving meal suggestions to history.
"""
import logging
from datetime import datetime
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.app.commands.meal_suggestion import SaveMealSuggestionCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.config import get_db
from src.infra.database.models.enums import MealTypeEnum, PlanDurationEnum, FitnessGoalEnum
from src.infra.database.models.meal_planning import (
    MealPlan as MealPlanORM,
    MealPlanDay as MealPlanDayORM,
    PlannedMeal as PlannedMealORM
)
from src.infra.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


@handles(SaveMealSuggestionCommand)
class SaveMealSuggestionCommandHandler(EventHandler[SaveMealSuggestionCommand, Dict[str, Any]]):
    """Handler for saving a meal suggestion to user's meal history."""
    
    def __init__(self, db: Session = None, user_repository=None):
        self.db = db
        self.user_repository = user_repository
    
    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        if 'db' in kwargs:
            self.db = kwargs['db']
        if 'user_repository' in kwargs:
            self.user_repository = kwargs['user_repository']
    
    async def handle(self, command: SaveMealSuggestionCommand) -> Dict[str, Any]:
        """
        Save a meal suggestion to the user's meal history.
        
        Args:
            command: SaveMealSuggestionCommand with suggestion data
        
        Returns:
            Dict with success status, message, meal_id, and meal_date
        """
        db = self.db or next(get_db())
        user_repo = self.user_repository or UserRepository(db)
        
        try:
            # Fetch user to get preferences
            user = user_repo.find_by_id(command.user_id)
            
            if not user:
                raise ValueError(f"User {command.user_id} not found")
            
            # Get user profile for preferences
            user_profile = user.profiles[0] if user.profiles else None
            
            # Create or find existing meal plan for this date
            meal_plan_orm = self._get_or_create_meal_plan(
                db, command.user_id, command.meal_date, user_profile
            )
            
            # Get or create day plan for the date
            day_plan_orm = self._get_or_create_day_plan(
                db, meal_plan_orm.id, command.meal_date
            )
            
            # Create the planned meal
            meal_orm = PlannedMealORM(
                day_id=day_plan_orm.id,
                meal_type=MealTypeEnum(command.meal_type),
                name=command.name,
                description=command.description,
                prep_time=command.estimated_cook_time_minutes // 2,  # Estimate prep as half
                cook_time=command.estimated_cook_time_minutes // 2,  # Estimate cook as half
                calories=command.calories,
                protein=command.protein,
                carbs=command.carbs,
                fat=command.fat,
                ingredients=command.ingredients_list,
                seasonings=[],  # Seasonings included in ingredients_list
                instructions=command.instructions,
                is_vegetarian="vegetarian" in [tag.lower() for tag in command.instructions] if command.instructions else False,
                is_vegan="vegan" in [tag.lower() for tag in command.instructions] if command.instructions else False,
                is_gluten_free="gluten-free" in [tag.lower() for tag in command.instructions] if command.instructions else False,
                cuisine_type="International"
            )
            
            db.add(meal_orm)
            db.commit()
            db.refresh(meal_orm)
            
            logger.info(
                f"Saved meal suggestion '{command.name}' for user {command.user_id} "
                f"on {command.meal_date}"
            )
            
            return {
                "success": True,
                "message": "Meal suggestion saved successfully to your meal history",
                "meal_id": str(meal_orm.id),
                "meal_date": command.meal_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error saving meal suggestion: {str(e)}")
            if db:
                db.rollback()
            raise
        finally:
            if self.db is None and db:
                db.close()
    
    def _get_or_create_meal_plan(
        self, 
        db: Session, 
        user_id: str, 
        meal_date, 
        user_profile
    ) -> MealPlanORM:
        """
        Get existing meal plan for the date or create a new one.
        
        Args:
            db: Database session
            user_id: User identifier
            meal_date: Date for the meal
            user_profile: User profile with preferences
        
        Returns:
            MealPlanORM instance
        """
        # Try to find existing meal plan for this user and date
        existing_plan = (
            db.query(MealPlanORM)
            .join(MealPlanDayORM)
            .filter(
                MealPlanORM.user_id == user_id,
                MealPlanDayORM.date == meal_date
            )
            .first()
        )
        
        if existing_plan:
            return existing_plan
        
        # Create new meal plan
        dietary_prefs = []
        allergies = []
        fitness_goal = FitnessGoalEnum.recomp
        meals_per_day = 3
        snacks_per_day = 0
        
        if user_profile:
            dietary_prefs = user_profile.dietary_preferences or []
            allergies = user_profile.allergies or []
            fitness_goal = FitnessGoalEnum(user_profile.fitness_goal) if user_profile.fitness_goal else FitnessGoalEnum.recomp
            meals_per_day = user_profile.meals_per_day or 3
            snacks_per_day = user_profile.snacks_per_day or 0
        
        meal_plan_orm = MealPlanORM(
            user_id=user_id,
            dietary_preferences=dietary_prefs,
            allergies=allergies,
            fitness_goal=fitness_goal,
            meals_per_day=meals_per_day,
            snacks_per_day=snacks_per_day,
            cooking_time_weekday=30,
            cooking_time_weekend=60,
            favorite_cuisines=[],
            disliked_ingredients=[],
            plan_duration=PlanDurationEnum.daily
        )
        
        db.add(meal_plan_orm)
        db.flush()
        
        return meal_plan_orm
    
    def _get_or_create_day_plan(
        self, 
        db: Session, 
        meal_plan_id: int, 
        meal_date
    ) -> MealPlanDayORM:
        """
        Get existing day plan or create a new one.
        
        Args:
            db: Database session
            meal_plan_id: Meal plan ID
            meal_date: Date for the day plan
        
        Returns:
            MealPlanDayORM instance
        """
        # Try to find existing day plan
        existing_day = (
            db.query(MealPlanDayORM)
            .filter(
                MealPlanDayORM.meal_plan_id == meal_plan_id,
                MealPlanDayORM.date == meal_date
            )
            .first()
        )
        
        if existing_day:
            return existing_day
        
        # Create new day plan
        day_plan_orm = MealPlanDayORM(
            meal_plan_id=meal_plan_id,
            date=meal_date
        )
        
        db.add(day_plan_orm)
        db.flush()
        
        return day_plan_orm



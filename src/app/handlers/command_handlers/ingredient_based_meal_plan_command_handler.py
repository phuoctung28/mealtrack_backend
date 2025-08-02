"""
Command handler for ingredient-based meal plan generation.
"""
import logging
from datetime import date
from datetime import datetime
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.app.commands.meal_plan import GenerateIngredientBasedMealPlanCommand
from src.app.events.base import EventHandler, handles
from src.app.handlers.command_handlers.user_command_handlers import SaveUserOnboardingCommandHandler
from src.domain.model.meal_plan import MealPlan, UserPreferences, DayPlan, DietaryPreference, FitnessGoal, PlanDuration, \
    PlannedMeal
from src.domain.services.ingredient_based_meal_plan_service import IngredientBasedMealPlanService
from src.infra.database.models.user import UserProfile
from src.infra.repositories.meal_plan_repository import MealPlanRepository

logger = logging.getLogger(__name__)


@handles(GenerateIngredientBasedMealPlanCommand)
class GenerateIngredientBasedMealPlanCommandHandler(
    EventHandler[GenerateIngredientBasedMealPlanCommand, Dict[str, Any]]
):
    """Handler for generating meal plans based on available ingredients and user profile."""

    def __init__(self, db: Session = None):
        self.db = db
        self.meal_plan_service = IngredientBasedMealPlanService()
        self.meal_plan_repository = MealPlanRepository(db)

    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db

    async def handle(self, command: GenerateIngredientBasedMealPlanCommand) -> Dict[str, Any]:
        """Generate a comprehensive meal plan based on available ingredients and user profile."""

        if not self.db:
            raise RuntimeError("Database session not configured")

        logger.info(f"Processing ingredient-based meal plan for user {command.user_id} with {len(command.available_ingredients)} ingredients")

        # Get user profile (or use defaults if not found)
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == command.user_id,
            UserProfile.is_current == True
        ).first()

        if profile:
            onboarding_handler = SaveUserOnboardingCommandHandler(self.db)
            tdee_result = onboarding_handler._calculate_tdee_and_macros(profile)

            dietary_preferences = profile.dietary_preferences or []
            allergies = profile.allergies or []
            target_calories = tdee_result['target_calories']
            target_protein = tdee_result['macros']['protein']
            target_carbs = tdee_result['macros']['carbs']
            target_fat = tdee_result['macros']['fat']
            meals_per_day = profile.meals_per_day
            include_snacks = (profile.snacks_per_day > 0)
            age = profile.age
            gender = profile.gender
            activity_level = profile.activity_level
            fitness_goal = profile.fitness_goal

        request_data = {
            "user_id": command.user_id,
            "available_ingredients": command.available_ingredients,
            "available_seasonings": command.available_seasonings,

            "dietary_preferences": dietary_preferences,
            "allergies": allergies,
            "cuisine_preferences": [],  # TODO onboarding

            "target_calories": target_calories,
            "target_protein": target_protein,
            "target_carbs": target_carbs,
            "target_fat": target_fat,

            "meals_per_day": meals_per_day,
            "include_snacks": include_snacks,
            "prep_time_limit": None,  # TODO onboarding
            "difficulty_level": "medium",  # TODO onboarding
            "minimize_waste": True,  # Default behavior
            "plan_date": date.today().isoformat(),

            "age": age,
            "gender": gender,
            "activity_level": activity_level,
            "fitness_goal": fitness_goal
        }

        try:
            meal_plan_result = self.meal_plan_service.generate_ingredient_based_meal_plan(request_data)

            logger.info(f"Successfully generated ingredient-based meal plan for user {command.user_id} with {len(meal_plan_result['meals'])} meals")

            # Save to database

            # Create UserPreferences from request_data
            preferences = UserPreferences(
                dietary_preferences=[DietaryPreference(pref) for pref in request_data.get('dietary_preferences', [])],
                allergies=request_data.get('allergies', []),
                fitness_goal=FitnessGoal(request_data.get('fitness_goal', 'maintenance')),
                meals_per_day=request_data.get('meals_per_day', 3),
                snacks_per_day=1 if request_data.get('include_snacks', False) else 0,
                cooking_time_weekday=30,  # Default
                cooking_time_weekend=45,  # Default
                favorite_cuisines=request_data.get('favorite_cuisines', []),
                disliked_ingredients=request_data.get('disliked_ingredients', []),
                plan_duration=PlanDuration.DAILY
            )

            # Create DayPlan
            day_plan = DayPlan(
                date=datetime.now().date(),
                meals=[PlannedMeal(**meal) for meal in meal_plan_result['meals']]
            )

            # Create MealPlan
            meal_plan = MealPlan(
                user_id=command.user_id,
                preferences=preferences,
                days=[day_plan]
            )

            # Save
            self.meal_plan_repository.save(meal_plan)

            # Add plan_id to result
            meal_plan_result['plan_id'] = meal_plan.plan_id

            return meal_plan_result

        except Exception as e:
            logger.error(f"Error generating ingredient-based meal plan: {str(e)}")
            raise
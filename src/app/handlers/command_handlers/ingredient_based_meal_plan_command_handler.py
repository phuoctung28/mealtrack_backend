"""
Command handler for ingredient-based meal plan generation.
"""
import logging
from datetime import date
from datetime import datetime
from typing import Dict, Any

from src.api.converters.meal_plan_converters import MealPlanConverter
from src.api.schemas.response.meal_plan_responses import DailyMealPlanStrongResponse
from src.app.handlers.query_handlers import GetUserTdeeQueryHandler
from src.app.handlers.command_handlers import SaveUserOnboardingCommandHandler
from src.app.queries.tdee.get_user_tdee_query import GetUserTdeeQuery

from sqlalchemy.orm import Session

from src.app.commands.meal_plan import GenerateIngredientBasedMealPlanCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.meal_plan import MealPlan, UserPreferences, DayPlan, DietaryPreference, FitnessGoal, PlanDuration, \
    PlannedMeal, MealType
from src.domain.services.ingredient_based_meal_plan_service import IngredientBasedMealPlanService
from src.infra.database.models.user import UserProfile
from src.infra.repositories.meal_plan_repository import MealPlanRepository

logger = logging.getLogger(__name__)


@handles(GenerateIngredientBasedMealPlanCommand)
class GenerateIngredientBasedMealPlanCommandHandler(
    EventHandler[GenerateIngredientBasedMealPlanCommand, DailyMealPlanStrongResponse]
):
    """Handler for generating meal plans based on available ingredients and user profile."""

    def __init__(self, db: Session = None):
        self.db = db
        self.meal_plan_service = IngredientBasedMealPlanService()
        self.meal_plan_repository = MealPlanRepository(db)

    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db

    async def handle(self, command: GenerateIngredientBasedMealPlanCommand) -> DailyMealPlanStrongResponse:
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
            tdee_handler = GetUserTdeeQueryHandler(self.db)
            tdee_query = GetUserTdeeQuery(user_id=command.user_id)
            tdee_result = await tdee_handler.handle(tdee_query)

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
            # Generate the meal plan (now returns DailyMealPlan domain model)
            daily_meal_plan = self.meal_plan_service.generate_ingredient_based_meal_plan(request_data)

            logger.info(f"Successfully generated ingredient-based meal plan for user {command.user_id} with {len(daily_meal_plan.meals)} meals")

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

            # Convert GeneratedMeal domain models to PlannedMeal entities for database
            planned_meals = []
            for generated_meal in daily_meal_plan.meals:
                # Convert GeneratedMeal to PlannedMeal for database storage
                planned_meal = PlannedMeal(
                    meal_id=generated_meal.meal_id,
                    meal_type=MealType(generated_meal.meal_type),
                    name=generated_meal.name,
                    description=generated_meal.description,
                    prep_time=generated_meal.prep_time,
                    cook_time=generated_meal.cook_time,
                    calories=generated_meal.nutrition.calories,
                    protein=generated_meal.nutrition.protein,
                    carbs=generated_meal.nutrition.carbs,
                    fat=generated_meal.nutrition.fat,
                    ingredients=generated_meal.ingredients,
                    instructions=generated_meal.instructions,
                    is_vegetarian=generated_meal.is_vegetarian,
                    is_vegan=generated_meal.is_vegan,
                    is_gluten_free=generated_meal.is_gluten_free,
                    cuisine_type=generated_meal.cuisine_type
                )
                planned_meals.append(planned_meal)
            
            # Create DayPlan
            day_plan = DayPlan(
                date=daily_meal_plan.plan_date,
                meals=planned_meals
            )

            # Create MealPlan entity for database
            meal_plan = MealPlan(
                user_id=command.user_id,
                preferences=preferences,
                days=[day_plan]
            )

            # Save to database
            self.meal_plan_repository.save(meal_plan)

            # Build the generation request to pass to converter
            from src.domain.model.meal_generation_request import (
                MealGenerationRequest, UserDietaryProfile, UserNutritionTargets
            )
            
            # Create the request object needed for the converter
            user_profile = UserDietaryProfile(
                user_id=command.user_id,
                dietary_preferences=dietary_preferences,
                health_conditions=[],
                allergies=allergies,
                activity_level=activity_level,
                fitness_goal=fitness_goal,
                meals_per_day=meals_per_day,
                include_snacks=include_snacks
            )
            
            nutrition_targets = UserNutritionTargets(
                calories=target_calories,
                protein=target_protein,
                carbs=target_carbs,
                fat=target_fat
            )
            
            generation_request = MealGenerationRequest(
                user_profile=user_profile,
                nutrition_targets=nutrition_targets,
                ingredient_constraints=None,  # Not needed for response conversion
                generation_type=None  # Not needed for response conversion
            )

            # Convert to API response model using the converter
            response = MealPlanConverter.daily_meal_plan_to_response(
                daily_meal_plan, 
                generation_request,
                plan_id=meal_plan.plan_id
            )

            return response

        except Exception as e:
            logger.error(f"Error generating ingredient-based meal plan: {str(e)}")
            raise
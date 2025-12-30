"""
Meal plan orchestration service.
Uses the unified LLM adapter with different prompts for different meal plan types.
"""
import logging
from datetime import date
from typing import Dict, Any

from src.domain.model.meal_planning import (
    DailyMealPlan, MealGenerationRequest, MealGenerationType,
    UserDietaryProfile, UserNutritionTargets, IngredientConstraints,
    MealGenerationContext, MealType
)
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.fallback_meal_service import FallbackMealService
from src.domain.services.meal_distribution_service import MealDistributionService
from src.domain.services.meal_type_determination_service import MealTypeDeterminationService
from src.domain.services.prompt_generation_service import PromptGenerationService
from src.domain.services.meal_plan.meal_plan_validator import MealPlanValidator
from src.domain.services.meal_plan.meal_plan_generator import MealPlanGenerator
from src.domain.services.meal_plan.meal_plan_formatter import MealPlanFormatter
from src.domain.services.meal_plan.request_builder import RequestBuilder

logger = logging.getLogger(__name__)


class MealPlanOrchestrationService:
    """
    Orchestrates meal plan generation using unified LLM service with different prompts.
    Handles all business logic while delegating LLM calls to the adapter.
    """

    def __init__(self, meal_generation_service: MealGenerationServicePort):
        self.meal_generation_service = meal_generation_service
        self.meal_distribution_service = MealDistributionService()
        self.meal_type_service = MealTypeDeterminationService()
        self.fallback_service = FallbackMealService()
        self.prompt_service = PromptGenerationService()

        # New extracted components
        self.validator = MealPlanValidator()
        self.generator = MealPlanGenerator(
            meal_generation_service, self.prompt_service, self.fallback_service
        )
        self.formatter = MealPlanFormatter()
        self.request_builder = RequestBuilder(self.meal_distribution_service, self.meal_type_service)

    def generate_weekly_ingredient_based_plan(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate weekly meal plan based on ingredients."""
        # Convert request data to domain model using request builder
        generation_request = self.request_builder.build_generation_request(
            request_data, MealGenerationType.WEEKLY_INGREDIENT_BASED
        )

        # Create generation context using request builder
        context = self.request_builder.create_generation_context(generation_request, request_data)

        try:
            # Generate prompt using domain service
            prompt, system_message = self.prompt_service.generate_prompt_and_system_message(context)

            # Generate using unified LLM service
            raw_data = self.meal_generation_service.generate_meal_plan(prompt, system_message, "json")

            # Validate using validator
            result = self.validator.validate_weekly_response(raw_data, request_data)
            if not result.is_valid:
                logger.warning(f"Validation warnings: {result.errors}")

            # Transform using formatter
            flat_meals = self.formatter.flatten_week(raw_data["week"])

            # Validate and adjust nutritional targets using formatter
            validated_meals = self.formatter.validate_and_adjust_weekly_nutrition(flat_meals, generation_request)

            return self.formatter.format_weekly_response(validated_meals, request_data)

        except Exception as e:
            logger.error(f"Error generating weekly meal plan: {str(e)}")
            logger.info("Falling back to individual daily meal generation")

            # Fallback: Generate day by day using generator
            fallback_meals = self.generator.generate_weekly_fallback(context, generation_request, request_data)

            # Convert generation_request back to request_data format for compatibility
            request_data_for_fallback = self.request_builder.convert_request_to_dict(generation_request, request_data)

            # Validate and adjust nutritional targets for fallback meals
            validated_meals = self.formatter.validate_and_adjust_weekly_nutrition(
                fallback_meals, generation_request
            )

            return self.formatter.format_weekly_response(validated_meals, request_data_for_fallback)

    def generate_daily_ingredient_based_plan(self, request_data: Dict[str, Any]) -> DailyMealPlan:
        """Generate daily meal plan based on ingredients."""
        # Convert request data to domain model using request builder
        generation_request = self.request_builder.build_generation_request(
            request_data, MealGenerationType.DAILY_INGREDIENT_BASED
        )

        # Create generation context using request builder
        context = self.request_builder.create_generation_context(generation_request)

        # Generate meals using generator
        return self.generator.generate_daily_plan(generation_request, context)

    def generate_daily_plan(self, user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Generate daily meal plan based on user preferences (non-ingredient based)."""
        # Convert request data to domain model using request builder
        generation_request = self.request_builder.build_generation_request(
            user_preferences, MealGenerationType.DAILY_PROFILE_BASED
        )

        # Create generation context using request builder
        context = self.request_builder.create_generation_context(generation_request)

        # Generate prompt using domain service
        prompt, system_message = self.prompt_service.generate_prompt_and_system_message(context)

        try:
            # Generate all meals using unified LLM service
            response_data = self.meal_generation_service.generate_meal_plan(prompt, system_message, "json")

            # Validate structure
            if "meals" not in response_data or not isinstance(response_data["meals"], list):
                raise ValueError("Response missing 'meals' array")

            # Convert to domain models using generator
            generated_meals = []
            for meal_data in response_data["meals"]:
                meal_type = MealType(meal_data.get("meal_type", "breakfast"))
                generated_meal = self.generator._convert_to_generated_meal(meal_data, meal_type)
                generated_meals.append(generated_meal)

            # Create daily meal plan domain model
            daily_plan = DailyMealPlan(
                user_id=generation_request.user_profile.user_id,
                plan_date=date.today(),
                meals=generated_meals
            )

            # Return the domain model directly
            return daily_plan

        except Exception as e:
            logger.error(f"Error generating unified daily meal plan: {str(e)}")
            # Fallback to individual meal generation
            logger.info("Falling back to individual meal generation")
            fallback_request_data = {
                **user_preferences,
                "available_ingredients": ["chicken", "rice", "vegetables", "eggs", "milk", "bread", "fruits"],
                "available_seasonings": ["salt", "pepper", "herbs", "spices"]
            }
            return self.generate_daily_ingredient_based_plan(fallback_request_data)

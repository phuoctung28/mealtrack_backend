"""
Converters for transforming domain models to API response models.
"""
from typing import Optional
from src.api.schemas.response.meal_plan_responses import (
    DailyMealPlanStrongResponse,
    GeneratedMealResponse,
    UserPreferencesStrongResponse
)
from src.domain.model.meal_generation_response import DailyMealPlan, GeneratedMeal, NutritionSummary
from src.domain.model.meal_generation_request import MealGenerationRequest


class MealPlanConverter:
    """Converter for meal plan domain models to API response models."""

    @staticmethod
    def nutrition_summary_to_response(nutrition: NutritionSummary) -> 'NutritionSummarySchema':
        """Convert domain NutritionSummary to response model."""
        from src.api.schemas.response.meal_plan_responses import NutritionSummarySchema
        return NutritionSummarySchema(
            calories=nutrition.calories,
            protein=round(nutrition.protein, 1),
            carbs=round(nutrition.carbs, 1),
            fat=round(nutrition.fat, 1)
        )

    @staticmethod
    def generated_meal_to_response(meal: GeneratedMeal) -> GeneratedMealResponse:
        """Convert domain GeneratedMeal to response model."""
        return GeneratedMealResponse(
            meal_id=meal.meal_id,
            meal_type=meal.meal_type,
            name=meal.name,
            description=meal.description,
            prep_time=meal.prep_time,
            cook_time=meal.cook_time,
            total_time=meal.total_time,
            calories=meal.nutrition.calories,
            protein=round(meal.nutrition.protein, 1),
            carbs=round(meal.nutrition.carbs, 1),
            fat=round(meal.nutrition.fat, 1),
            ingredients=meal.ingredients,
            instructions=meal.instructions,
            is_vegetarian=meal.is_vegetarian,
            is_vegan=meal.is_vegan,
            is_gluten_free=meal.is_gluten_free,
            cuisine_type=meal.cuisine_type
        )

    @staticmethod
    def user_preferences_to_response(request: MealGenerationRequest) -> 'UserPreferencesStrongResponse':
        """Convert domain MealGenerationRequest to user preferences response."""
        from src.api.schemas.response.meal_plan_responses import UserPreferencesStrongResponse
        return UserPreferencesStrongResponse(
            dietary_preferences=request.user_profile.dietary_preferences or [],
            health_conditions=request.user_profile.health_conditions or [],
            allergies=request.user_profile.allergies or [],
            activity_level=request.user_profile.activity_level,
            fitness_goal=request.user_profile.fitness_goal,
            meals_per_day=request.user_profile.meals_per_day,
            snacks_per_day=1 if request.user_profile.include_snacks else 0
        )

    @staticmethod
    def daily_meal_plan_to_response(
        daily_plan: DailyMealPlan, 
        request: MealGenerationRequest,
        plan_id: Optional[str] = None
    ) -> 'DailyMealPlanStrongResponse':
        """Convert domain DailyMealPlan to response model."""
        from src.api.schemas.response.meal_plan_responses import DailyMealPlanStrongResponse
        return DailyMealPlanStrongResponse(
            user_id=daily_plan.user_id,
            date=daily_plan.plan_date.isoformat(),
            plan_id=plan_id,
            meals=[
                MealPlanConverter.generated_meal_to_response(meal) 
                for meal in daily_plan.meals
            ],
            total_nutrition=MealPlanConverter.nutrition_summary_to_response(daily_plan.total_nutrition),
            target_nutrition=MealPlanConverter.nutrition_summary_to_response(request.nutrition_targets),
            user_preferences=MealPlanConverter.user_preferences_to_response(request)
        )
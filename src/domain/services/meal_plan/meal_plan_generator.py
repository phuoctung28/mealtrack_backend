"""Meal plan generation logic."""
import logging
from typing import Dict, Any, List
from datetime import date, datetime, timedelta

from src.domain.model.meal_planning import (
    DailyMealPlan, GeneratedMeal, NutritionSummary, MealType,
    MealGenerationRequest, MealGenerationContext
)
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.fallback_meal_service import FallbackMealService
from src.domain.services.prompt_generation_service import PromptGenerationService

logger = logging.getLogger(__name__)


class MealPlanGenerator:
    """Generates meal plans using LLM and fallback strategies."""

    def __init__(
        self,
        meal_generation_service: MealGenerationServicePort,
        prompt_service: PromptGenerationService,
        fallback_service: FallbackMealService
    ):
        self.meal_generation_service = meal_generation_service
        self.prompt_service = prompt_service
        self.fallback_service = fallback_service

    def generate_daily_plan(
        self,
        generation_request: MealGenerationRequest,
        context: MealGenerationContext
    ) -> DailyMealPlan:
        """Generate daily meal plan with fallback."""
        generated_meals = []
        total_nutrition = NutritionSummary(calories=0, protein=0.0, carbs=0.0, fat=0.0)

        for meal_type in context.meal_types:
            calorie_target = context.calorie_distribution.get_calories_for_meal(meal_type)

            try:
                # Generate prompt for this specific meal
                prompt, system_message = self.prompt_service.generate_single_meal_prompt(
                    meal_type, calorie_target, context
                )

                # Generate using unified LLM service
                meal_data = self.meal_generation_service.generate_meal_plan(prompt, system_message, "json")

                # Convert to domain model
                generated_meal = self._convert_to_generated_meal(meal_data, meal_type)
                generated_meals.append(generated_meal)

                # Add to totals
                total_nutrition.calories += generated_meal.nutrition.calories
                total_nutrition.protein += generated_meal.nutrition.protein
                total_nutrition.carbs += generated_meal.nutrition.carbs
                total_nutrition.fat += generated_meal.nutrition.fat

            except Exception as e:
                logger.error(f"Error generating {meal_type.value} meal: {str(e)}")
                # Use fallback meal from domain service
                fallback_meal = self.fallback_service.get_fallback_meal(meal_type, calorie_target)
                generated_meals.append(fallback_meal)

                total_nutrition.calories += fallback_meal.nutrition.calories
                total_nutrition.protein += fallback_meal.nutrition.protein
                total_nutrition.carbs += fallback_meal.nutrition.carbs
                total_nutrition.fat += fallback_meal.nutrition.fat

        # Create daily meal plan domain model
        return DailyMealPlan(
            user_id=generation_request.user_profile.user_id,
            plan_date=date.today(),
            meals=generated_meals
        )

    def generate_weekly_fallback(
        self,
        context: MealGenerationContext,
        generation_request: MealGenerationRequest,
        request_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate weekly plan using fallback meals when LLM generation fails."""
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        all_meals = []

        # Use provided start date if available, otherwise calculate current week
        if request_data and "start_date_obj" in request_data:
            start_date = request_data["start_date_obj"]
        else:
            # Fallback to current week calculation
            today = datetime.now().date()
            days_since_monday = today.weekday()
            start_date = today - timedelta(days=days_since_monday)

        # Generate meals for each day using fallback service
        for i, day_name in enumerate(days):
            for meal_type in context.meal_types:
                calorie_target = context.calorie_distribution.get_calories_for_meal(meal_type)
                fallback_meal = self.fallback_service.get_fallback_meal(meal_type, calorie_target)

                # Calculate date for this day
                day_date = start_date + timedelta(days=i)

                # Convert to dict format expected by weekly response
                meal_dict = {
                    "day": day_name,
                    "date": day_date.isoformat(),
                    "day_formatted": f"{day_name}, {day_date.strftime('%B %d, %Y')}",
                    "meal_type": fallback_meal.meal_type,
                    "name": fallback_meal.name,
                    "description": fallback_meal.description,
                    "calories": fallback_meal.nutrition.calories,
                    "protein": fallback_meal.nutrition.protein,
                    "carbs": fallback_meal.nutrition.carbs,
                    "fat": fallback_meal.nutrition.fat,
                    "prep_time": fallback_meal.prep_time,
                    "cook_time": fallback_meal.cook_time,
                    "ingredients": fallback_meal.ingredients,
                    "seasonings": fallback_meal.seasonings,
                    "instructions": fallback_meal.instructions,
                    "is_vegetarian": fallback_meal.is_vegetarian,
                    "is_vegan": fallback_meal.is_vegan,
                    "is_gluten_free": fallback_meal.is_gluten_free,
                    "cuisine_type": fallback_meal.cuisine_type
                }
                all_meals.append(meal_dict)

        return all_meals

    def _convert_to_generated_meal(self, meal_data: Dict[str, Any], meal_type: MealType) -> GeneratedMeal:
        """Convert LLM response to domain model."""
        nutrition = NutritionSummary(
            calories=int(meal_data.get("calories", 0)),
            protein=float(meal_data.get("protein", 0.0)),
            carbs=float(meal_data.get("carbs", 0.0)),
            fat=float(meal_data.get("fat", 0.0))
        )

        return GeneratedMeal(
            meal_id=f"meal_{meal_type.value}_{hash(str(meal_data)) % 10000}",
            meal_type=meal_type.value,
            name=meal_data.get("name", f"Simple {meal_type.value.title()}"),
            description=meal_data.get("description", f"A nutritious {meal_type.value}"),
            prep_time=meal_data.get("prep_time", 15),
            cook_time=meal_data.get("cook_time", 20),
            nutrition=nutrition,
            ingredients=meal_data.get("ingredients", ["Basic ingredients"]),
            seasonings=meal_data.get("seasonings", ["Basic seasonings"]),
            instructions=meal_data.get("instructions", ["Prepare and cook as desired"]),
            is_vegetarian=meal_data.get("is_vegetarian", False),
            is_vegan=meal_data.get("is_vegan", False),
            is_gluten_free=meal_data.get("is_gluten_free", False),
            cuisine_type=meal_data.get("cuisine_type", "International")
        )

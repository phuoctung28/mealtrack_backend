import logging
from typing import List, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from src.domain.model.meal_planning import PlannedMeal, MealType
from src.domain.services.meal_suggestion.json_extractor import JsonExtractor
from src.domain.services.fallback_meal_service import FallbackMealService
from src.domain.services.meal_suggestion.suggestion_prompt_builder import SuggestionPromptBuilder
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort

logger = logging.getLogger(__name__)


class DailyMealSuggestionService:
    """Service for generating daily meal suggestions based on user preferences from onboarding"""

    def __init__(self, generation_service: Optional[MealGenerationServicePort] = None):
        """
        Initialize with optional generation service (dependency injection).
        If not provided, will use default implementation at runtime.
        """
        self._generation_service = generation_service

        # Initialize extracted components
        self.json_extractor = JsonExtractor()
        self.fallback_service = FallbackMealService()
        self.prompt_builder = SuggestionPromptBuilder()

    def generate_daily_suggestions(self, user_preferences: Dict) -> List[PlannedMeal]:
        """
        Generate 3-5 meal suggestions for a day based on user onboarding data

        Args:
            user_preferences: Dictionary containing user data from onboarding
                - age, gender, height, weight
                - activity_level: sedentary/lightly_active/moderately_active/very_active/extra_active
                - goal: lose_weight/maintain_weight/gain_weight/build_muscle
                - dietary_preferences: List of dietary restrictions
                - health_conditions: List of health conditions
                - target_calories: Daily calorie target
                - target_macros: Daily macro targets (protein, carbs, fat)

        Returns:
            List of 3-5 PlannedMeal objects
        """
        logger.info(f"Generating daily meal suggestions for user preferences")

        # Use the new unified generation method
        return self._generate_all_meals_unified(user_preferences)

    def _generate_all_meals_unified(self, user_preferences: Dict) -> List[PlannedMeal]:
        """Generate all daily meals in a single request"""

        # Determine meal distribution based on calories
        target_calories = user_preferences.get('target_calories')
        if not target_calories:
            raise ValueError("target_calories is required for meal suggestions. Please provide user's calculated TDEE.")
        meal_distribution = self._calculate_meal_distribution(target_calories)

        # Build unified prompt using prompt builder
        prompt = self.prompt_builder.build_unified_meal_prompt(meal_distribution, user_preferences)

        try:
            # Use injected generation service or get default
            if not self._generation_service:
                # Lazy import to avoid circular dependency
                from src.infra.services.ai.gemini_meal_generation_service import GeminiMealGenerationService
                self._generation_service = GeminiMealGenerationService()
            
            # Call generation service through port
            system_message = "You are a professional nutritionist creating personalized daily meal plans."
            response_data = self._generation_service.generate_meal_plan(
                prompt=prompt,
                system_message=system_message,
                response_type="json"
            )
            
            # Extract JSON using json extractor (handles the response format)
            daily_meals_data = self.json_extractor.extract_unified_meals_json(str(response_data))

            # Convert to PlannedMeal objects
            suggested_meals = []
            for meal_data in daily_meals_data["meals"]:
                meal_type = MealType(meal_data["meal_type"])
                meal = PlannedMeal(
                    meal_type=meal_type,
                    name=meal_data["name"],
                    description=meal_data["description"],
                    prep_time=meal_data.get("prep_time", 10),
                    cook_time=meal_data.get("cook_time", 15),
                    calories=meal_data["calories"],
                    protein=meal_data["protein"],
                    carbs=meal_data["carbs"],
                    fat=meal_data["fat"],
                    ingredients=meal_data["ingredients"],
                    instructions=meal_data.get("instructions", ["Prepare and cook as desired"]),
                    is_vegetarian=meal_data.get("is_vegetarian", False),
                    is_vegan=meal_data.get("is_vegan", False),
                    is_gluten_free=meal_data.get("is_gluten_free", False),
                    cuisine_type=meal_data.get("cuisine_type", "International")
                )
                suggested_meals.append(meal)

            return suggested_meals

        except Exception as e:
            logger.error(f"Error generating unified meals: {str(e)}")
            # Fallback to individual meal generation
            logger.info("Falling back to individual meal generation")
            return self._generate_meals_individual(meal_distribution, user_preferences)

    def _generate_meals_individual(self, meal_distribution: Dict[MealType, float], user_preferences: Dict) -> List[PlannedMeal]:
        """Fallback method: Generate meals individually (original method)"""
        suggested_meals = []

        for meal_type, calorie_target in meal_distribution.items():
            try:
                meal = self._generate_meal_for_type(
                    meal_type=meal_type,
                    calorie_target=calorie_target,
                    user_preferences=user_preferences
                )
                suggested_meals.append(meal)
            except Exception as e:
                logger.error(f"Error generating {meal_type.value} meal: {str(e)}")
                # Add a fallback meal using fallback service
                fallback_meal = self.fallback_service.get_fallback_meal(meal_type, int(calorie_target))
                # Convert GeneratedMeal to PlannedMeal
                planned_meal = PlannedMeal(
                    meal_type=meal_type,
                    name=fallback_meal.name,
                    description=fallback_meal.description,
                    prep_time=fallback_meal.prep_time,
                    cook_time=fallback_meal.cook_time,
                    calories=fallback_meal.nutrition.calories,
                    protein=fallback_meal.nutrition.protein,
                    carbs=fallback_meal.nutrition.carbs,
                    fat=fallback_meal.nutrition.fat,
                    ingredients=fallback_meal.ingredients,
                    seasonings=fallback_meal.seasonings,
                    instructions=fallback_meal.instructions,
                    is_vegetarian=fallback_meal.is_vegetarian,
                    is_vegan=fallback_meal.is_vegan,
                    is_gluten_free=fallback_meal.is_gluten_free,
                    cuisine_type=fallback_meal.cuisine_type
                )
                suggested_meals.append(planned_meal)

        return suggested_meals

    def _calculate_meal_distribution(self, total_calories: float) -> Dict[MealType, float]:
        """Calculate calorie distribution across meals"""
        from src.domain.constants import MealDistribution

        # Standard distribution
        distribution = {
            MealType.BREAKFAST: total_calories * MealDistribution.BREAKFAST_PERCENT,
            MealType.LUNCH: total_calories * MealDistribution.LUNCH_PERCENT,
            MealType.DINNER: total_calories * MealDistribution.DINNER_PERCENT,
        }

        # Add snack if total calories > threshold
        if total_calories > MealDistribution.MIN_CALORIES_FOR_SNACK:
            distribution[MealType.SNACK] = total_calories * MealDistribution.SNACK_PERCENT
            # Adjust other meals
            distribution[MealType.BREAKFAST] = total_calories * MealDistribution.BREAKFAST_WITH_SNACK
            distribution[MealType.LUNCH] = total_calories * MealDistribution.LUNCH_WITH_SNACK
            distribution[MealType.DINNER] = total_calories * MealDistribution.DINNER_WITH_SNACK

        return distribution

    def _generate_meal_for_type(self, meal_type: MealType, calorie_target: float,
                                user_preferences: Dict) -> PlannedMeal:
        """Generate a single meal based on type and preferences"""

        # Build prompt using prompt builder
        prompt = self.prompt_builder.build_meal_suggestion_prompt(meal_type, calorie_target, user_preferences)

        try:
            messages = [
                SystemMessage(content="You are a professional nutritionist creating personalized meal suggestions."),
                HumanMessage(content=prompt)
            ]

            response = self.model.invoke(messages)
            content = response.content

            # Extract JSON using json extractor
            meal_data = self.json_extractor.extract_json(content)

            # Create PlannedMeal object
            return PlannedMeal(
                meal_type=meal_type,
                name=meal_data["name"],
                description=meal_data["description"],
                prep_time=meal_data.get("prep_time", 10),
                cook_time=meal_data.get("cook_time", 15),
                calories=meal_data["calories"],
                protein=meal_data["protein"],
                carbs=meal_data["carbs"],
                fat=meal_data["fat"],
                ingredients=meal_data["ingredients"],
                instructions=meal_data.get("instructions", ["Prepare and cook as desired"]),
                is_vegetarian=meal_data.get("is_vegetarian", False),
                is_vegan=meal_data.get("is_vegan", False),
                is_gluten_free=meal_data.get("is_gluten_free", False),
                cuisine_type=meal_data.get("cuisine_type", "International")
            )

        except Exception as e:
            logger.error(f"Error generating meal: {str(e)}")
            raise

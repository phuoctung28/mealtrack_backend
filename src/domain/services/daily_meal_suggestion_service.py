import json
import logging
import os
from typing import List, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.domain.model.meal_planning import PlannedMeal, MealType
from src.domain.services.meal_suggestion.json_extractor import JsonExtractor
from src.domain.services.meal_suggestion.suggestion_fallback_provider import SuggestionFallbackProvider
from src.domain.services.meal_suggestion.suggestion_prompt_builder import SuggestionPromptBuilder

logger = logging.getLogger(__name__)


class DailyMealSuggestionService:
    """Service for generating daily meal suggestions based on user preferences from onboarding"""

    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        self.model = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            temperature=0.7,
            max_output_tokens=4000,  # Increased for multiple meals
            google_api_key=self.google_api_key,
            convert_system_message_to_human=True
        )

        # Initialize extracted components
        self.json_extractor = JsonExtractor()
        self.fallback_provider = SuggestionFallbackProvider()
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
            messages = [
                SystemMessage(content="You are a professional nutritionist creating personalized daily meal plans."),
                HumanMessage(content=prompt)
            ]

            response = self.model.invoke(messages)
            content = response.content

            # Extract JSON using json extractor
            daily_meals_data = self.json_extractor.extract_unified_meals_json(content)

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
                # Add a fallback meal using fallback provider
                suggested_meals.append(self.fallback_provider.get_fallback_meal(meal_type, calorie_target))

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

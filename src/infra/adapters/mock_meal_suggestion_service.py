"""
Mock Meal Suggestion Service for testing.
"""
from typing import List, Dict, Any
from datetime import date

from src.domain.ports.meal_suggestion_service_port import MealSuggestionServicePort
from src.domain.model.meal_suggestion import MealSuggestion, MealType
from src.domain.model.macros import Macros


class MockMealSuggestionService(MealSuggestionServicePort):
    """Mock implementation of meal suggestion service for testing."""
    
    def generate_suggestions(
        self,
        target_calories: float,
        dietary_preferences: List[str] = None,
        health_conditions: List[str] = None
    ) -> List[MealSuggestion]:
        """Generate mock meal suggestions."""
        # Calculate meal calories based on typical distribution
        breakfast_calories = target_calories * 0.25
        lunch_calories = target_calories * 0.35
        dinner_calories = target_calories * 0.30
        snack_calories = target_calories * 0.10
        
        suggestions = [
            MealSuggestion(
                meal_type=MealType.BREAKFAST,
                dish_name="Oatmeal with Berries and Nuts",
                description="Whole grain oats topped with fresh berries and almonds",
                calories=breakfast_calories,
                macros=Macros(
                    protein=breakfast_calories * 0.15 / 4,  # 15% from protein, 4 cal/g
                    carbs=breakfast_calories * 0.60 / 4,    # 60% from carbs, 4 cal/g
                    fat=breakfast_calories * 0.25 / 9,      # 25% from fat, 9 cal/g
                    fiber=8.0
                ),
                ingredients=[
                    "Rolled oats", "Blueberries", "Strawberries", 
                    "Almonds", "Honey", "Cinnamon"
                ],
                prep_time_minutes=10,
                cooking_instructions=[
                    "Cook oats according to package directions",
                    "Top with fresh berries",
                    "Add sliced almonds and drizzle with honey",
                    "Sprinkle with cinnamon"
                ]
            ),
            MealSuggestion(
                meal_type=MealType.LUNCH,
                dish_name="Grilled Chicken Salad",
                description="Mixed greens with grilled chicken breast and vegetables",
                calories=lunch_calories,
                macros=Macros(
                    protein=lunch_calories * 0.35 / 4,
                    carbs=lunch_calories * 0.40 / 4,
                    fat=lunch_calories * 0.25 / 9,
                    fiber=12.0
                ),
                ingredients=[
                    "Chicken breast", "Mixed greens", "Cherry tomatoes",
                    "Cucumber", "Avocado", "Olive oil", "Lemon"
                ],
                prep_time_minutes=20,
                cooking_instructions=[
                    "Season and grill chicken breast",
                    "Prepare salad with mixed greens and vegetables",
                    "Slice grilled chicken and place on salad",
                    "Dress with olive oil and lemon juice"
                ]
            ),
            MealSuggestion(
                meal_type=MealType.DINNER,
                dish_name="Salmon with Quinoa and Vegetables",
                description="Baked salmon fillet with quinoa and roasted vegetables",
                calories=dinner_calories,
                macros=Macros(
                    protein=dinner_calories * 0.30 / 4,
                    carbs=dinner_calories * 0.45 / 4,
                    fat=dinner_calories * 0.25 / 9,
                    fiber=10.0
                ),
                ingredients=[
                    "Salmon fillet", "Quinoa", "Broccoli", "Carrots",
                    "Bell peppers", "Garlic", "Olive oil", "Herbs"
                ],
                prep_time_minutes=30,
                cooking_instructions=[
                    "Preheat oven to 400°F",
                    "Season salmon and bake for 15-20 minutes",
                    "Cook quinoa according to package directions",
                    "Roast vegetables with olive oil and garlic",
                    "Serve salmon over quinoa with vegetables"
                ]
            ),
            MealSuggestion(
                meal_type=MealType.SNACK,
                dish_name="Greek Yogurt with Nuts",
                description="Plain Greek yogurt topped with mixed nuts",
                calories=snack_calories,
                macros=Macros(
                    protein=snack_calories * 0.30 / 4,
                    carbs=snack_calories * 0.40 / 4,
                    fat=snack_calories * 0.30 / 9,
                    fiber=2.0
                ),
                ingredients=[
                    "Greek yogurt", "Walnuts", "Almonds", "Honey"
                ],
                prep_time_minutes=5,
                cooking_instructions=[
                    "Spoon yogurt into bowl",
                    "Top with mixed nuts",
                    "Drizzle with honey if desired"
                ]
            )
        ]
        
        # Adjust suggestions based on dietary preferences
        if dietary_preferences:
            if "vegetarian" in dietary_preferences:
                # Replace chicken with tofu in lunch
                suggestions[1].dish_name = "Tofu Salad"
                suggestions[1].ingredients[0] = "Tofu"
                # Replace salmon with lentils in dinner
                suggestions[2].dish_name = "Lentil Curry with Quinoa"
                suggestions[2].ingredients[0] = "Red lentils"
        
        return suggestions
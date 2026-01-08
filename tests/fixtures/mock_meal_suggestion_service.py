"""
Mock Meal Suggestion Service for testing.
"""
import uuid
from typing import List, Dict, Any

from src.domain.model.meal_planning import MealType, PlannedMeal


class MockMealSuggestionService:
    """Mock implementation of meal suggestion service for testing."""
    
    def generate_suggestions(
        self,
        target_calories: float,
        dietary_preferences: List[str] = None,
        health_conditions: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate mock meal suggestions."""
        # Calculate meal calories based on typical distribution
        breakfast_calories = target_calories * 0.25
        lunch_calories = target_calories * 0.35
        dinner_calories = target_calories * 0.30
        snack_calories = target_calories * 0.10
        
        suggestions = [
            {
                "meal_type": MealType.BREAKFAST.value,
                "dish_name": "Oatmeal with Berries and Nuts",
                "description": "Whole grain oats topped with fresh berries and almonds",
                "calories": breakfast_calories,
                "macros": {
                    "protein": breakfast_calories * 0.15 / 4,  # 15% from protein, 4 cal/g
                    "carbs": breakfast_calories * 0.60 / 4,    # 60% from carbs, 4 cal/g
                    "fat": breakfast_calories * 0.25 / 9,      # 25% from fat, 9 cal/g
                },
                "ingredients": [
                    "Rolled oats", "Blueberries", "Strawberries", 
                    "Almonds", "Honey", "Cinnamon"
                ],
                "prep_time_minutes": 10,
                "cooking_instructions": [
                    "Cook oats according to package directions",
                    "Top with fresh berries",
                    "Add sliced almonds and drizzle with honey",
                    "Sprinkle with cinnamon"
                ]
            },
            {
                "meal_type": MealType.LUNCH.value,
                "dish_name": "Grilled Chicken Salad",
                "description": "Mixed greens with grilled chicken breast and vegetables",
                "calories": lunch_calories,
                "macros": {
                    "protein": lunch_calories * 0.35 / 4,
                    "carbs": lunch_calories * 0.40 / 4,
                    "fat": lunch_calories * 0.25 / 9,
                    "": 12.0
                },
                "ingredients": [
                    "Chicken breast", "Mixed greens", "Cherry tomatoes",
                    "Cucumber", "Avocado", "Olive oil", "Lemon"
                ],
                "prep_time_minutes": 20,
                "cooking_instructions": [
                    "Season and grill chicken breast",
                    "Prepare salad with mixed greens and vegetables",
                    "Slice grilled chicken and place on salad",
                    "Dress with olive oil and lemon juice"
                ]
            },
            {
                "meal_type": MealType.DINNER.value,
                "dish_name": "Salmon with Quinoa and Vegetables",
                "description": "Baked salmon fillet with quinoa and roasted vegetables",
                "calories": dinner_calories,
                "macros": {
                    "protein": dinner_calories * 0.30 / 4,
                    "carbs": dinner_calories * 0.45 / 4,
                    "fat": dinner_calories * 0.25 / 9,
                },
                "ingredients": [
                    "Salmon fillet", "Quinoa", "Broccoli", "Carrots",
                    "Bell peppers", "Garlic", "Olive oil", "Herbs"
                ],
                "prep_time_minutes": 30,
                "cooking_instructions": [
                    "Preheat oven to 400°F",
                    "Season salmon and bake for 15-20 minutes",
                    "Cook quinoa according to package directions",
                    "Roast vegetables with olive oil and garlic",
                    "Serve salmon over quinoa with vegetables"
                ]
            },
            {
                "meal_type": MealType.SNACK.value,
                "dish_name": "Greek Yogurt with Nuts",
                "description": "Plain Greek yogurt topped with mixed nuts",
                "calories": snack_calories,
                "macros": {
                    "protein": snack_calories * 0.30 / 4,
                    "carbs": snack_calories * 0.40 / 4,
                    "fat": snack_calories * 0.30 / 9,
                },
                "ingredients": [
                    "Greek yogurt", "Walnuts", "Almonds", "Honey"
                ],
                "prep_time_minutes": 5,
                "cooking_instructions": [
                    "Spoon yogurt into bowl",
                    "Top with mixed nuts",
                    "Drizzle with honey if desired"
                ]
            }
        ]
        
        # Adjust suggestions based on dietary preferences
        if dietary_preferences:
            if "vegetarian" in dietary_preferences:
                # Replace chicken with tofu in lunch
                suggestions[1]["dish_name"] = "Tofu Salad"
                suggestions[1]["ingredients"][0] = "Tofu"
                # Replace salmon with lentils in dinner
                suggestions[2]["dish_name"] = "Lentil Curry with Quinoa"
                suggestions[2]["ingredients"][0] = "Red lentils"
        
        return suggestions
    
    def generate_daily_suggestions(self, user_data: Dict[str, Any]) -> List[PlannedMeal]:
        """Generate daily meal suggestions based on user data."""
        target_calories = user_data.get('target_calories')
        if not target_calories:
            raise ValueError("target_calories is required in user_data for mock service")
        dietary_preferences = user_data.get('dietary_preferences', [])
        
        # Get suggestions in dict format
        suggestions_data = self.generate_suggestions(
            target_calories,
            dietary_preferences,
            user_data.get('health_conditions', [])
        )
        
        # Convert to PlannedMeal objects
        planned_meals = []
        for suggestion in suggestions_data:
            meal = PlannedMeal(
                meal_id=str(uuid.uuid4()),
                meal_type=MealType(suggestion['meal_type']),
                name=suggestion['dish_name'],
                description=suggestion['description'],
                prep_time=suggestion['prep_time_minutes'],
                cook_time=suggestion['prep_time_minutes'],  # Using same as prep for mock
                calories=int(suggestion['calories']),
                protein=suggestion['macros']['protein'],
                carbs=suggestion['macros']['carbs'],
                fat=suggestion['macros']['fat'],
                ingredients=suggestion['ingredients'],
                instructions=suggestion['cooking_instructions'],
                is_vegetarian='vegetarian' in dietary_preferences,
                is_vegan='vegan' in dietary_preferences,
                is_gluten_free='gluten_free' in dietary_preferences,
                cuisine_type='American'
            )
            planned_meals.append(meal)
        
        return planned_meals
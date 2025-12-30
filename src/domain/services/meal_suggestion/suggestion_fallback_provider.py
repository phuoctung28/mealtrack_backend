"""Fallback meal provider for suggestion service."""
from src.domain.model.meal_planning import PlannedMeal, MealType


class SuggestionFallbackProvider:
    """Provides fallback meals when AI generation fails."""

    @staticmethod
    def get_fallback_meal(meal_type: MealType, calorie_target: float) -> PlannedMeal:
        """Return a simple fallback meal if generation fails."""
        # Scale portions based on calorie target
        scale_factor = calorie_target / 400  # Base meals are ~400 calories

        fallback_meals = {
            MealType.BREAKFAST: {
                "name": "Protein Oatmeal Bowl",
                "description": "Hearty oatmeal with protein powder and fruits",
                "prep_time": 5,
                "cook_time": 5,
                "calories": int(400 * scale_factor),
                "protein": int(25 * scale_factor),
                "carbs": int(55 * scale_factor),
                "fat": int(10 * scale_factor),
                "ingredients": [
                    f"{int(60 * scale_factor)}g rolled oats",
                    f"{int(30 * scale_factor)}g protein powder",
                    "1 medium banana",
                    "1 tablespoon almond butter",
                    "Cinnamon to taste"
                ],
                "instructions": [
                    "Cook oats with water or milk",
                    "Stir in protein powder",
                    "Top with sliced banana and almond butter",
                    "Sprinkle with cinnamon"
                ],
                "is_vegetarian": True,
                "is_vegan": False,
                "is_gluten_free": False
            },
            MealType.LUNCH: {
                "name": "Grilled Chicken Salad Bowl",
                "description": "Fresh salad with grilled chicken and vegetables",
                "prep_time": 15,
                "cook_time": 15,
                "calories": int(450 * scale_factor),
                "protein": int(35 * scale_factor),
                "carbs": int(30 * scale_factor),
                "fat": int(20 * scale_factor),
                "ingredients": [
                    f"{int(150 * scale_factor)}g grilled chicken breast",
                    "Mixed greens",
                    "Cherry tomatoes",
                    "Cucumber",
                    "Avocado",
                    "Olive oil vinaigrette"
                ],
                "instructions": [
                    "Grill chicken breast",
                    "Prepare salad greens and vegetables",
                    "Slice grilled chicken",
                    "Assemble bowl and dress"
                ],
                "is_vegetarian": False,
                "is_vegan": False,
                "is_gluten_free": True
            },
            MealType.DINNER: {
                "name": "Baked Salmon with Vegetables",
                "description": "Omega-3 rich salmon with roasted vegetables",
                "prep_time": 10,
                "cook_time": 25,
                "calories": int(500 * scale_factor),
                "protein": int(40 * scale_factor),
                "carbs": int(35 * scale_factor),
                "fat": int(22 * scale_factor),
                "ingredients": [
                    f"{int(180 * scale_factor)}g salmon fillet",
                    "Broccoli",
                    "Sweet potato",
                    "Olive oil",
                    "Lemon",
                    "Herbs"
                ],
                "instructions": [
                    "Season salmon with herbs",
                    "Prepare vegetables",
                    "Bake everything at 400°F for 20-25 minutes",
                    "Serve with lemon"
                ],
                "is_vegetarian": False,
                "is_vegan": False,
                "is_gluten_free": True
            },
            MealType.SNACK: {
                "name": "Greek Yogurt with Berries",
                "description": "High-protein snack with antioxidants",
                "prep_time": 2,
                "cook_time": 0,
                "calories": int(200 * scale_factor),
                "protein": int(15 * scale_factor),
                "carbs": int(20 * scale_factor),
                "fat": int(5 * scale_factor),
                "ingredients": [
                    f"{int(170 * scale_factor)}g Greek yogurt",
                    "Mixed berries",
                    "Honey (optional)"
                ],
                "instructions": [
                    "Add berries to yogurt",
                    "Drizzle with honey if desired"
                ],
                "is_vegetarian": True,
                "is_vegan": False,
                "is_gluten_free": True
            }
        }

        meal_data = fallback_meals.get(meal_type, fallback_meals[MealType.LUNCH])
        return PlannedMeal(meal_type=meal_type, **meal_data)

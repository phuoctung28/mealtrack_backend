"""
Domain service for providing fallback meals when generation fails.
"""
from typing import Dict
from src.domain.model.meal_plan import MealType
from src.domain.model.meal_generation_response import GeneratedMeal, NutritionSummary


class FallbackMealService:
    """Service for providing fallback meals when AI generation fails."""
    
    def get_fallback_meal(self, meal_type: MealType, calorie_target: int) -> GeneratedMeal:
        """Get a fallback meal for the specified type and calorie target."""
        # Scale portions based on calorie target
        scale_factor = calorie_target / 400  # Base meals are ~400 calories
        
        fallback_templates = self._get_fallback_templates()
        template = fallback_templates.get(meal_type, fallback_templates[MealType.LUNCH])
        
        # Scale nutrition and portions
        scaled_nutrition = NutritionSummary(
            calories=int(template["base_calories"] * scale_factor),
            protein=template["base_protein"] * scale_factor,
            carbs=template["base_carbs"] * scale_factor,
            fat=template["base_fat"] * scale_factor
        )
        
        # Scale ingredient portions
        scaled_ingredients = []
        for ingredient in template["ingredients"]:
            if "{portion}" in ingredient:
                portion = int(template.get("base_portion", 100) * scale_factor)
                scaled_ingredients.append(ingredient.format(portion=portion))
            else:
                scaled_ingredients.append(ingredient)
        
        return GeneratedMeal(
            meal_id=f"fallback_{meal_type.value}_{calorie_target}",
            meal_type=meal_type.value,
            name=template["name"],
            description=template["description"],
            prep_time=template["prep_time"],
            cook_time=template["cook_time"],
            nutrition=scaled_nutrition,
            ingredients=scaled_ingredients,
            instructions=template["instructions"],
            is_vegetarian=template["is_vegetarian"],
            is_vegan=template["is_vegan"],
            is_gluten_free=template["is_gluten_free"],
            cuisine_type=template["cuisine_type"]
        )
    
    def _get_fallback_templates(self) -> Dict[MealType, Dict]:
        """Get fallback meal templates."""
        return {
            MealType.BREAKFAST: {
                "name": "Protein Oatmeal Bowl",
                "description": "Hearty oatmeal with protein powder and fruits",
                "prep_time": 5,
                "cook_time": 5,
                "base_calories": 400,
                "base_protein": 25.0,
                "base_carbs": 55.0,
                "base_fat": 10.0,
                "base_portion": 60,
                "ingredients": [
                    "{portion}g rolled oats",
                    "30g protein powder",
                    "1 medium banana",
                    "1 tbsp almond butter"
                ],
                "instructions": [
                    "Cook oats with water or milk",
                    "Stir in protein powder",
                    "Top with sliced banana and almond butter"
                ],
                "is_vegetarian": True,
                "is_vegan": False,
                "is_gluten_free": False,
                "cuisine_type": "International"
            },
            MealType.LUNCH: {
                "name": "Grilled Chicken Salad Bowl",
                "description": "Fresh salad with grilled chicken and vegetables",
                "prep_time": 15,
                "cook_time": 15,
                "base_calories": 450,
                "base_protein": 35.0,
                "base_carbs": 30.0,
                "base_fat": 20.0,
                "base_portion": 150,
                "ingredients": [
                    "{portion}g grilled chicken breast",
                    "Mixed greens",
                    "Cherry tomatoes",
                    "Cucumber",
                    "Avocado"
                ],
                "instructions": [
                    "Grill chicken breast",
                    "Prepare salad greens and vegetables",
                    "Slice grilled chicken",
                    "Assemble bowl and dress"
                ],
                "is_vegetarian": False,
                "is_vegan": False,
                "is_gluten_free": True,
                "cuisine_type": "International"
            },
            MealType.DINNER: {
                "name": "Baked Salmon with Vegetables",
                "description": "Omega-3 rich salmon with roasted vegetables",
                "prep_time": 10,
                "cook_time": 25,
                "base_calories": 500,
                "base_protein": 40.0,
                "base_carbs": 35.0,
                "base_fat": 22.0,
                "base_portion": 180,
                "ingredients": [
                    "{portion}g salmon fillet",
                    "Broccoli",
                    "Sweet potato",
                    "Olive oil",
                    "Lemon"
                ],
                "instructions": [
                    "Season salmon with herbs",
                    "Prepare vegetables",
                    "Bake everything at 400°F for 20-25 minutes",
                    "Serve with lemon"
                ],
                "is_vegetarian": False,
                "is_vegan": False,
                "is_gluten_free": True,
                "cuisine_type": "International"
            },
            MealType.SNACK: {
                "name": "Greek Yogurt with Berries",
                "description": "High-protein snack with antioxidants",
                "prep_time": 2,
                "cook_time": 0,
                "base_calories": 200,
                "base_protein": 15.0,
                "base_carbs": 20.0,
                "base_fat": 5.0,
                "base_portion": 170,
                "ingredients": [
                    "{portion}g Greek yogurt",
                    "Mixed berries",
                    "Honey (optional)"
                ],
                "instructions": [
                    "Add berries to yogurt",
                    "Drizzle with honey if desired"
                ],
                "is_vegetarian": True,
                "is_vegan": False,
                "is_gluten_free": True,
                "cuisine_type": "International"
            }
        }
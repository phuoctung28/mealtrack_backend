"""
Fallback meal generation service.
Provides default meals when AI generation fails.
"""
import logging
from typing import List, Dict, Optional

from src.domain.model.meal_suggestion import MealSuggestion, MacroEstimate

logger = logging.getLogger(__name__)


class MealFallbackService:
    """
    Provides fallback meal suggestions when AI generation fails.
    Uses pre-defined healthy meal templates.
    """

    # Fallback meal templates by type
    FALLBACK_TEMPLATES: Dict[str, List[Dict]] = {
        "breakfast": [
            {
                "name": "Oatmeal with Berries",
                "description": "Hearty oatmeal topped with fresh berries and honey",
                "calories": 350,
                "protein": 12,
                "carbs": 55,
                "fat": 8,
                "ingredients": [
                    {"name": "rolled oats", "amount": 80, "unit": "g"},
                    {"name": "mixed berries", "amount": 100, "unit": "g"},
                    {"name": "honey", "amount": 15, "unit": "ml"},
                    {"name": "almond milk", "amount": 200, "unit": "ml"},
                ],
                "recipe_steps": [
                    {"step": 1, "instruction": "Cook oats in almond milk", "duration_minutes": 5},
                    {"step": 2, "instruction": "Top with berries and honey", "duration_minutes": 2},
                ],
                "prep_time_minutes": 10,
            },
            {
                "name": "Greek Yogurt Parfait",
                "description": "Creamy yogurt layered with granola and fruit",
                "calories": 400,
                "protein": 20,
                "carbs": 45,
                "fat": 12,
                "ingredients": [
                    {"name": "Greek yogurt", "amount": 200, "unit": "g"},
                    {"name": "granola", "amount": 50, "unit": "g"},
                    {"name": "banana", "amount": 1, "unit": "medium"},
                    {"name": "honey", "amount": 10, "unit": "ml"},
                ],
                "recipe_steps": [
                    {"step": 1, "instruction": "Layer yogurt in bowl", "duration_minutes": 1},
                    {"step": 2, "instruction": "Add granola and sliced banana", "duration_minutes": 2},
                    {"step": 3, "instruction": "Drizzle with honey", "duration_minutes": 1},
                ],
                "prep_time_minutes": 5,
            },
        ],
        "lunch": [
            {
                "name": "Grilled Chicken Salad",
                "description": "Fresh mixed greens with grilled chicken and vinaigrette",
                "calories": 450,
                "protein": 35,
                "carbs": 25,
                "fat": 22,
                "ingredients": [
                    {"name": "chicken breast", "amount": 150, "unit": "g"},
                    {"name": "mixed greens", "amount": 150, "unit": "g"},
                    {"name": "cherry tomatoes", "amount": 100, "unit": "g"},
                    {"name": "olive oil", "amount": 20, "unit": "ml"},
                    {"name": "balsamic vinegar", "amount": 15, "unit": "ml"},
                ],
                "recipe_steps": [
                    {"step": 1, "instruction": "Grill chicken breast until cooked through", "duration_minutes": 15},
                    {"step": 2, "instruction": "Slice chicken and arrange on greens", "duration_minutes": 3},
                    {"step": 3, "instruction": "Add tomatoes and dress with oil and vinegar", "duration_minutes": 2},
                ],
                "prep_time_minutes": 20,
            },
            {
                "name": "Turkey Sandwich",
                "description": "Whole grain sandwich with turkey and vegetables",
                "calories": 500,
                "protein": 30,
                "carbs": 45,
                "fat": 18,
                "ingredients": [
                    {"name": "whole grain bread", "amount": 2, "unit": "slices"},
                    {"name": "turkey breast", "amount": 120, "unit": "g"},
                    {"name": "lettuce", "amount": 30, "unit": "g"},
                    {"name": "tomato", "amount": 50, "unit": "g"},
                    {"name": "avocado", "amount": 40, "unit": "g"},
                ],
                "recipe_steps": [
                    {"step": 1, "instruction": "Toast bread lightly", "duration_minutes": 2},
                    {"step": 2, "instruction": "Layer turkey, lettuce, tomato, and avocado", "duration_minutes": 3},
                    {"step": 3, "instruction": "Season and close sandwich", "duration_minutes": 1},
                ],
                "prep_time_minutes": 10,
            },
        ],
        "dinner": [
            {
                "name": "Baked Salmon with Vegetables",
                "description": "Herb-crusted salmon with roasted seasonal vegetables",
                "calories": 550,
                "protein": 40,
                "carbs": 30,
                "fat": 28,
                "ingredients": [
                    {"name": "salmon fillet", "amount": 180, "unit": "g"},
                    {"name": "broccoli", "amount": 150, "unit": "g"},
                    {"name": "sweet potato", "amount": 150, "unit": "g"},
                    {"name": "olive oil", "amount": 15, "unit": "ml"},
                    {"name": "lemon", "amount": 1, "unit": "wedge"},
                ],
                "recipe_steps": [
                    {"step": 1, "instruction": "Preheat oven to 200°C", "duration_minutes": 5},
                    {"step": 2, "instruction": "Season salmon and arrange vegetables on baking sheet", "duration_minutes": 5},
                    {"step": 3, "instruction": "Bake for 20 minutes until salmon is cooked", "duration_minutes": 20},
                ],
                "prep_time_minutes": 30,
            },
            {
                "name": "Chicken Stir-Fry",
                "description": "Quick stir-fried chicken with colorful vegetables",
                "calories": 480,
                "protein": 38,
                "carbs": 35,
                "fat": 18,
                "ingredients": [
                    {"name": "chicken breast", "amount": 180, "unit": "g"},
                    {"name": "bell peppers", "amount": 100, "unit": "g"},
                    {"name": "broccoli", "amount": 100, "unit": "g"},
                    {"name": "brown rice", "amount": 80, "unit": "g"},
                    {"name": "soy sauce", "amount": 20, "unit": "ml"},
                ],
                "recipe_steps": [
                    {"step": 1, "instruction": "Cook rice according to package", "duration_minutes": 15},
                    {"step": 2, "instruction": "Stir-fry chicken until golden", "duration_minutes": 8},
                    {"step": 3, "instruction": "Add vegetables and soy sauce, cook until tender", "duration_minutes": 5},
                ],
                "prep_time_minutes": 25,
            },
        ],
    }

    def get_fallback_meals(
        self,
        meal_type: str,
        count: int = 2,
        target_calories: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get fallback meal suggestions.
        
        Args:
            meal_type: Type of meal (breakfast, lunch, dinner)
            count: Number of meals to return
            target_calories: Optional calorie target for filtering
            
        Returns:
            List of fallback meal dictionaries
        """
        templates = self.FALLBACK_TEMPLATES.get(
            meal_type.lower(), 
            self.FALLBACK_TEMPLATES["lunch"]
        )
        
        # Filter by calories if target specified
        if target_calories:
            margin = 100  # Allow 100 cal margin
            templates = [
                t for t in templates 
                if abs(t["calories"] - target_calories) <= margin
            ] or templates  # Fallback to all if none match
        
        return templates[:count]

    def generate_fallback_suggestion(
        self,
        session_id: str,
        user_id: str,
        meal_type: str,
        index: int = 0,
    ) -> MealSuggestion:
        """
        Generate a fallback MealSuggestion from templates.
        
        Args:
            session_id: Session ID
            user_id: User ID
            meal_type: Type of meal
            index: Template index to use
            
        Returns:
            MealSuggestion object
        """
        from src.domain.model.meal_suggestion import (
            Ingredient,
            RecipeStep,
            MealType as SuggestionMealType,
        )
        import uuid
        
        templates = self.FALLBACK_TEMPLATES.get(
            meal_type.lower(),
            self.FALLBACK_TEMPLATES["lunch"]
        )
        template = templates[index % len(templates)]
        
        return MealSuggestion(
            id=f"fallback_{uuid.uuid4().hex[:16]}",
            session_id=session_id,
            user_id=user_id,
            meal_name=template["name"],
            description=template["description"],
            meal_type=SuggestionMealType(meal_type.lower()),
            macros=MacroEstimate(
                calories=template["calories"],
                protein=template["protein"],
                carbs=template["carbs"],
                fat=template["fat"],
            ),
            ingredients=[Ingredient(**ing) for ing in template["ingredients"]],
            recipe_steps=[RecipeStep(**step) for step in template["recipe_steps"]],
            prep_time_minutes=template["prep_time_minutes"],
            confidence_score=0.7,  # Lower confidence for fallback
        )

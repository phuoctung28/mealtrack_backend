"""
Prompt templates for unified daily meal plan generation.
Generates all meals for a day in a single API call.
"""
from typing import Dict, Any

from src.domain.model.macro_targets import SimpleMacroTargets
from src.domain.model.meal_plan import MealType


def build_unified_meal_prompt(meal_distribution: Dict[MealType, float], user_preferences: Dict[str, Any]) -> str:
    """Build a unified prompt for generating all daily meals at once"""
    
    # Extract user data
    goal = user_preferences.get('goal', 'maintain_weight')
    dietary_prefs = user_preferences.get('dietary_preferences', [])
    health_conditions = user_preferences.get('health_conditions', [])
    target_macros = user_preferences.get('target_macros', {})
    activity_level = user_preferences.get('activity_level', 'moderately_active')
    target_calories = user_preferences.get('target_calories', 2000)
    
    # Build dietary restrictions string
    dietary_str = ", ".join(dietary_prefs) if dietary_prefs else "none"
    health_str = ", ".join(health_conditions) if health_conditions else "none"
    
    # Goal-specific guidance
    goal_guidance = {
        'lose_weight': "Focus on high-volume, low-calorie foods with plenty of fiber and protein for satiety",
        'gain_weight': "Include calorie-dense, nutritious foods with healthy fats and complex carbs",
        'build_muscle': "Emphasize high protein content with complete amino acids",
        'maintain_weight': "Create balanced meals with appropriate portions"
    }
    
    # Build meal targets string
    meal_targets = []
    for meal_type, calorie_target in meal_distribution.items():
        meal_percentage = calorie_target / target_calories
        
        # Handle both MacroTargets object and dict format
        if isinstance(target_macros, SimpleMacroTargets):
            protein_target = target_macros.protein * meal_percentage
            carbs_target = target_macros.carbs * meal_percentage
            fat_target = target_macros.fat * meal_percentage
        else:
            # Legacy dict format
            protein_target = target_macros.get('protein_grams', 50) * meal_percentage
            carbs_target = target_macros.get('carbs_grams', 250) * meal_percentage
            fat_target = target_macros.get('fat_grams', 65) * meal_percentage
        
        meal_targets.append(f"""
{meal_type.value.title()}:
- Calories: {int(calorie_target)} (±50 calories)
- Protein: {int(protein_target)}g
- Carbs: {int(carbs_target)}g
- Fat: {int(fat_target)}g""")
    
    meal_targets_str = "\n".join(meal_targets)
    
    return f"""Generate a complete daily meal plan with these requirements:

User Profile:
- Fitness Goal: {goal} - {goal_guidance.get(goal, 'balanced nutrition')}
- Activity Level: {activity_level}
- Dietary Restrictions: {dietary_str}
- Health Conditions: {health_str}
- Total Daily Calories: {int(target_calories)}

Nutritional Targets for each meal:
{meal_targets_str}

Requirements:
1. All meals should be practical and use common ingredients
2. Cooking times should be reasonable for each meal type
3. Must respect all dietary restrictions across all meals
4. Should support the user's fitness goal
5. Include variety and flavor across the day
6. Ensure meals complement each other for a balanced day

Return ONLY a JSON object with this structure:
{{
    "meals": [
        {{
            "meal_type": "breakfast",
            "name": "Meal name",
            "description": "Brief appealing description",
            "prep_time": 10,
            "cook_time": 20,
            "calories": 500,
            "protein": 25,
            "carbs": 60,
            "fat": 15,
            "ingredients": ["ingredient 1 with amount", "ingredient 2 with amount"],
            "instructions": ["Step 1", "Step 2"],
            "is_vegetarian": true/false,
            "is_vegan": true/false,
            "is_gluten_free": true/false,
            "cuisine_type": "cuisine type"
        }},
        // ... repeat for each meal type
    ]
}}"""


def get_system_message() -> str:
    """Get system message for unified meal planning."""
    return "You are a professional nutritionist creating personalized daily meal plans."
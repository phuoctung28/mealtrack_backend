"""
Prompt templates for daily meal plan generation.
"""
from typing import Dict, Any

from src.domain.model.macro_targets import SimpleMacroTargets
from src.domain.model.meal_plan import MealType


def build_single_meal_prompt(meal_type: MealType, calorie_target: float, user_preferences: Dict[str, Any]) -> str:
    """Build prompt for generating a single meal."""
    
    # Extract user data
    goal = user_preferences.get('goal', 'maintain_weight')
    dietary_prefs = user_preferences.get('dietary_preferences', [])
    health_conditions = user_preferences.get('health_conditions', [])
    target_macros = user_preferences.get('target_macros', {})
    activity_level = user_preferences.get('activity_level', 'moderately_active')
    
    # Calculate macro targets for this meal
    meal_percentage = calorie_target / user_preferences.get('target_calories', 2000)
    
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
    
    return f"""Generate a {meal_type.value} meal suggestion with these requirements:

User Profile:
- Fitness Goal: {goal} - {goal_guidance.get(goal, 'balanced nutrition')}
- Activity Level: {activity_level}
- Dietary Restrictions: {dietary_str}
- Health Conditions: {health_str}

Nutritional Targets for this meal:
- Calories: {int(calorie_target)} (±50 calories)
- Protein: {int(protein_target)}g
- Carbs: {int(carbs_target)}g
- Fat: {int(fat_target)}g

Requirements:
1. The meal should be practical and use common ingredients
2. Cooking time should be reasonable for {meal_type.value}
3. Must respect all dietary restrictions
4. Should support the user's fitness goal
5. Include variety and flavor

Return ONLY a JSON object with this structure:
{{
    "name": "Meal name",
    "description": "Brief appealing description",
    "prep_time": 10,
    "cook_time": 20,
    "calories": {int(calorie_target)},
    "protein": {int(protein_target)},
    "carbs": {int(carbs_target)},
    "fat": {int(fat_target)},
    "ingredients": ["ingredient 1 with amount", "ingredient 2 with amount"],
    "instructions": ["Step 1", "Step 2"],
    "is_vegetarian": true/false,
    "is_vegan": true/false,
    "is_gluten_free": true/false,
    "cuisine_type": "cuisine type"
}}"""


def build_ingredient_based_meal_prompt(meal_type: MealType, calorie_target: int, request_data: Dict[str, Any]) -> str:
    """Build prompt for ingredient-based meal generation."""
    
    available_ingredients = request_data.get('available_ingredients', [])
    available_seasonings = request_data.get('available_seasonings', [])
    dietary_preferences = request_data.get('dietary_preferences', [])
    allergies = request_data.get('allergies', [])
    
    # Format ingredients list
    ingredients_text = ", ".join(available_ingredients)
    seasonings_text = ", ".join(available_seasonings) if available_seasonings else "basic seasonings"
    
    prompt = f"""Create a {meal_type.value} recipe using these available ingredients: {ingredients_text}
Available seasonings: {seasonings_text}
Target calories: {calorie_target}

IMPORTANT: Only use the ingredients listed above. Do not add any other ingredients.
"""
    
    if dietary_preferences:
        prompt += f"Dietary preferences: {', '.join(dietary_preferences)}\n"
    
    if allergies:
        prompt += f"Allergies to avoid: {', '.join(allergies)}\n"
    
    prompt += f"""
Create a simple, practical recipe that:
- Uses ONLY the available ingredients listed above
- Creates a balanced and nutritious {meal_type.value}
- Is easy to prepare
- CRITICAL: NEVER use any ingredients that match the allergies listed above

Respond with valid JSON only:
{{
    "name": "Recipe Name",
    "description": "Brief description",
    "calories": {calorie_target},
    "protein": 25.0,
    "carbs": 35.0,
    "fat": 15.0,
    "prep_time": 15,
    "cook_time": 20,
    "ingredients": ["chicken", "broccoli", "rice"],
    "instructions": ["step 1", "step 2"],
    "is_vegetarian": false,
    "is_vegan": false,
    "is_gluten_free": true,
    "cuisine_type": "International"
}}"""
    
    return prompt


def get_system_message() -> str:
    """Get system message for daily meal planning."""
    return "You are a professional nutritionist creating personalized meal suggestions."
"""
Prompt templates for daily meal plan generation.
"""
from typing import Dict, Any

from src.domain.model.meal_planning import MealType
from src.domain.model.meal_planning import SimpleMacroTargets


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


def build_quick_meal_suggestions_prompt(
    meal_type: str,
    ingredients: list[str],
    time_filter: str | None = None,
    count: int = 6
) -> str:
    """
    Build prompt for quick meal suggestions with enriched output.

    Args:
        meal_type: Type of meal (breakfast, lunch, dinner, snack)
        ingredients: List of available/desired ingredients
        time_filter: Optional time constraint (any, quick, moderate, extended)
        count: Number of meal ideas to generate (default 6)

    Returns:
        Prompt string for AI generation
    """

    # Build ingredients text
    ingredients_text = ", ".join(ingredients) if ingredients else "any common ingredients"

    # Build time constraint section
    time_constraint = ""
    if time_filter and time_filter != "any":
        time_limits = {
            "quick": ("under 15 minutes", 15),
            "moderate": ("15-30 minutes", 30),
            "extended": ("30-60 minutes", 60),
        }
        description, max_time = time_limits.get(time_filter, ("any time", 999))
        time_constraint = f"""
Time Constraint: {description}
- All meals MUST be completable within {max_time} minutes total
- Prioritize quick cooking methods if needed
"""

    return f"""Generate {count} quick {meal_type} meal ideas using these ingredients: {ingredients_text}
{time_constraint}
Requirements:
1. Each meal should prominently feature the provided ingredients
2. Include practical, achievable recipes
3. Vary the cooking styles and cuisines
4. Be creative but realistic

For each meal, provide:
- name: Catchy meal name
- description: Short tagline (10 words max)
- time_minutes: Total cooking time in minutes
- calories: Estimated calories
- protein_g, carbs_g, fat_g: Macros in grams
- pairs_with: List of 3-5 complementary ingredients that would enhance this meal
- quick_recipe: List of 4-6 simple cooking steps
- tags: List of relevant tags like "quick", "high-protein", "low-carb", etc.

Return ONLY a JSON object with this structure:
{{
    "meals": [
        {{
            "name": "Meal Name",
            "description": "Quick, flavorful tagline",
            "time_minutes": 15,
            "calories": 400,
            "protein_g": 30.0,
            "carbs_g": 40.0,
            "fat_g": 12.0,
            "pairs_with": ["avocado", "lemon", "cherry tomatoes"],
            "quick_recipe": [
                "Season the protein with salt and pepper",
                "Heat pan with olive oil",
                "Cook until golden",
                "Serve with sides"
            ],
            "tags": ["quick", "high-protein", "low-carb"]
        }}
    ]
}}

Generate exactly {count} different meal ideas."""
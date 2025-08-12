"""
Prompt templates for weekly meal plan generation.
"""
from typing import Dict, Any


def build_weekly_ingredient_based_prompt(request: Dict[str, Any]) -> str:
    """Build optimized prompt for weekly ingredient-based meal plans."""
    ing = ", ".join(request.get("available_ingredients", [])) or "(any)"
    season = ", ".join(request.get("available_seasonings", [])) or "basic spices"
    dietary_prefs = request.get("dietary_preferences", [])
    meals_per_day = request.get("meals_per_day", 3)
    include_snacks = request.get("include_snacks", False)
    target_calories = request.get("target_calories", 2000)
    
    # Define meal types based on configuration
    meal_types = ["breakfast", "lunch", "dinner"]
    if meals_per_day == 4:
        meal_types.append("lunch")  # Add second lunch or brunch
    
    snack_requirement = ""
    if include_snacks:
        meal_types.append("snack")
        snack_requirement = "\n6. Include 1 healthy snack per day."
    
    schema = (
        '{"week":[{"day":"Monday","meals":[{"meal_type":"breakfast","name":"…",'
        '"description":"…","calories":450,"protein":25.0,"carbs":55.0,"fat":15.0,'
        '"prep_time":10,"cook_time":15,"ingredients":["…"],"instructions":["…"],'
        '"is_vegetarian":true,"is_vegan":false,"is_gluten_free":false,"cuisine_type":"International"}]},'
        '{"day":"Tuesday","meals":[]}, "…"]}'
    )

    dietary_requirements = ""
    if dietary_prefs:
        dietary_requirements = f"\nDietary preferences: {', '.join(dietary_prefs)}"

    calorie_guidance = f"\nDaily target: ~{target_calories} calories total per day"

    return (
        f"Generate a concise 7-day meal plan (Monday-Sunday) using only available ingredients.\n"
        f"Ingredients: {ing}\n"
        f"Seasonings: {season}{dietary_requirements}{calorie_guidance}\n"
        f"Meal types required: {', '.join(meal_types)}\n"
        "Rules:\n"
        "1. Use ONLY listed ingredients - no exceptions.\n"
        "2. Generate exactly 3 main meals per day" + (" + 1 snack" if include_snacks else "") + ".\n"
        "3. Each meal must have: meal_type, name, description, calories, protein, carbs, fat, prep_time, cook_time, ingredients, instructions, is_vegetarian, is_vegan, is_gluten_free, cuisine_type.\n"
        "4. Accurate nutritional values and dietary flags.\n"
        "5. Keep instructions concise (3-5 steps max)." + snack_requirement + "\n"
        f"Output ONLY valid JSON:\n{schema}"
    )


def get_system_message() -> str:
    """Get optimized system message for meal planning."""
    return "Meal planner. JSON only, no markdown."
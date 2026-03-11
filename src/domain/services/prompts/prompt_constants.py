"""
Centralized prompt constants with compressed templates.
Reduces prompt tokens by ~40-60% through deduplication.
"""
from typing import Dict


# =============================================================================
# INGREDIENT RULES (Compressed)
# =============================================================================
INGREDIENT_RULES = (
    "INGREDIENTS: Use ONLY listed items with exact portions (g/ml). "
    "Format: '300g rice', '450g chicken', '100g greens'. "
    "All items MUST have amounts. NO bare items like 'tomatoes'."
)

INGREDIENT_RULES_DETAILED = (
    "INGREDIENT REQUIREMENTS:\n"
    "- ALL ingredients MUST have exact portions (g/ml/pieces)\n"
    "- Use metric units only: grams (g), milliliters (ml)\n"
    "- Proteins: 400-600g, Grains: 200-400g, Vegetables: 100-300g\n"
    "- Example: ['450g chicken', '300g rice', '150g broccoli', '15ml oil']"
)


# =============================================================================
# SEASONING RULES (Compressed)
# =============================================================================
SEASONING_RULES = (
    "SEASONINGS: Exact amounts (g/ml). "
    "Example: ['2g salt', '1g pepper', '3g oregano']"
)

SEASONING_RULES_DETAILED = (
    "SEASONINGS REQUIREMENTS:\n"
    "- All seasonings MUST have exact amounts (g/ml)\n"
    "- Salt: 1-3g, Pepper: 0.5-1g, Herbs: 2-5g, Oils: 5-15ml\n"
    "- Example: ['2g salt', '1g pepper', '3g oregano', '5ml sesame oil']"
)


# =============================================================================
# NUTRITION RULES (Compressed)
# =============================================================================
NUTRITION_RULES = (
    "Match target calories (±50). Balance protein/carbs/fat per meal type."
)

# =============================================================================
# MACRO ACCURACY RULES — appended to recipe generation prompts
# =============================================================================
MACRO_ACCURACY_RULES = (
    "UNIT CONVERSION (MANDATORY):\n"
    "- Convert ALL quantities to grams before calculating macros\n"
    "- Liquid densities: honey=1.42g/ml, oil/butter=0.92g/ml, milk=1.03g/ml, "
    "soy sauce=1.2g/ml, yogurt=1.05g/ml, cream=1.01g/ml\n"
    "- Unknown liquids: assume 1.0g/ml (water density)\n"
    "- Return all ingredient amounts in GRAMS (not ml, cups, tbsp)\n"
    "  Example: '75ml honey' → '106g honey' (density 1.42)\n"
    "\n"
    "MACRO CALCULATION (MANDATORY):\n"
    "- Calculate each ingredient's macros from per-100g nutrition data\n"
    "- Sum all ingredient macros to get total macros\n"
    "- Verify: calories = protein*4 + carbs*4 + fat*9 (must match within 5%)\n"
    "- If mismatch: recalculate calories from macros\n"
)

# =============================================================================
# DECOMPOSITION RULES — enforce ingredient-level breakdown
# =============================================================================
DECOMPOSITION_RULES = (
    "INGREDIENT DECOMPOSITION (MANDATORY):\n"
    "- ALWAYS break down compound dishes into individual ingredients\n"
    "- Never return a single entry for a multi-ingredient dish\n"
    "- Minimum 3 ingredients per dish (most real dishes have 4+)\n"
    "- Simple foods (banana, egg, plain rice) may stay as 1 item\n"
    "- Examples:\n"
    "  ✅ 'pho bo' → rice noodle (200g), beef (100g), broth (400g), bean sprouts (50g), herbs (20g), oil (5g)\n"
    "  ✅ 'pasta carbonara' → spaghetti (180g), bacon (60g), egg (50g), parmesan (30g), cream (30g)\n"
    "  ❌ 'pho bo' → 1 entry with 450 kcal\n"
)


# =============================================================================
# JSON SCHEMAS (Compressed - No inline comments)
# =============================================================================
JSON_SCHEMAS: Dict[str, str] = {
    "weekly_meal": '''{
  "week": [{
    "day": "Monday",
    "meals": [{
      "meal_type": "breakfast",
      "name": "Meal Name",
      "description": "Brief description",
      "calories": 400,
      "protein": 25.0,
      "carbs": 45.0,
      "fat": 15.0,
      "prep_time": 10,
      "cook_time": 15,
      "ingredients": ["300g rice", "450g chicken"],
      "seasonings": ["2g salt", "1g pepper"],
      "instructions": ["step1", "step2"],
      "is_vegetarian": false,
      "is_vegan": false,
      "is_gluten_free": false,
      "cuisine_type": "International"
    }]
  }]
}''',
    
    "daily_meal": '''{
  "meals": [{
    "meal_type": "breakfast",
    "name": "Name",
    "description": "Description",
    "calories": 400,
    "protein": 25.0,
    "carbs": 45.0,
    "fat": 15.0,
    "prep_time": 10,
    "cook_time": 15,
    "ingredients": ["300g rice", "450g chicken"],
    "seasonings": ["2g salt", "1g pepper"],
    "instructions": ["step1", "step2"],
    "is_vegetarian": false,
    "is_vegan": false,
    "is_gluten_free": false,
    "cuisine_type": "International"
  }]
}''',

    "single_meal": '''{
  "name": "Name",
  "description": "Description",
  "calories": 400,
  "protein": 25.0,
  "carbs": 45.0,
  "fat": 15.0,
  "prep_time": 10,
  "cook_time": 15,
  "ingredients": ["300g rice", "450g chicken"],
  "seasonings": ["2g salt", "1g pepper"],
  "instructions": ["step1", "step2"],
  "is_vegetarian": false,
  "is_vegan": false,
  "is_gluten_free": false,
  "cuisine_type": "International"
}''',

    "suggestion_recipe": '''{
  "name": "Dish Name",
  "description": "Brief description",
  "cuisine_type": "Asian",
  "origin_country": "Vietnam",
  "ingredients": [
    {"name": "ingredient1", "amount": 200, "unit": "g"},
    {"name": "ingredient2", "amount": 100, "unit": "g"}
  ],
  "recipe_steps": [
    {"step": 1, "instruction": "Action", "duration_minutes": 5},
    {"step": 2, "instruction": "Action", "duration_minutes": 10}
  ],
  "prep_time_minutes": 20
}'''
}


# =============================================================================
# GOAL GUIDANCE (Compressed)
# =============================================================================
GOAL_GUIDANCE = {
    "lose_weight": "High-volume, low-calorie, fiber-rich, high-protein",
    "gain_weight": "Calorie-dense, healthy fats, complex carbs",
    "build_muscle": "High protein, complete amino acids",
    "maintain_weight": "Balanced portions",
    "cut": "High-volume, low-calorie, fiber-rich, high-protein",
    "bulk": "Calorie-dense, healthy fats, complex carbs", 
    "recomp": "Balanced macros, moderate deficit"
}


# =============================================================================
# SYSTEM MESSAGES (Compressed)
# =============================================================================
SYSTEM_MESSAGES = {
    "meal_planning": "You are a meal planning assistant. Return only valid JSON.",
    "nutritionist": "You are a professional nutritionist. Return only valid JSON.",
    "chef": "You are a professional chef. Generate complete recipe details as valid JSON.",
    "creative_chef": "You are a creative chef. Generate diverse meal names with different cuisines.",
}

# =============================================================================
# LANGUAGE NAMES (Compressed)
# =============================================================================
LANGUAGE_NAMES = {
    "en": "English",
    "vi": "Vietnamese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "zh": "Chinese",
}


# =============================================================================
# FALLBACK MEAL NAMES (English-only, will be translated in Phase 3)
# =============================================================================
def get_fallback_meal_name(language: str, meal_type: str, index: int) -> str:
    """Get English fallback meal name.
    
    Note: Always returns English names. Translation happens in Phase 3 if needed.

    Args:
        language: ISO 639-1 language code (ignored, always uses English)
        meal_type: Meal type ('breakfast', 'lunch', 'dinner', 'snack')
        index: Index number for the fallback (1-based)

    Returns:
        English fallback name like "Healthy Breakfast #1"
    """
    base_name = f"Healthy {meal_type.title()}"
    return f"{base_name} #{index}"
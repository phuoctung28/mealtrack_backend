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
# FALLBACK MEAL NAMES (Localized)
# =============================================================================
FALLBACK_MEAL_NAMES = {
    "en": {
        "breakfast": "Healthy Breakfast",
        "lunch": "Healthy Lunch",
        "dinner": "Healthy Dinner",
        "snack": "Healthy Snack",
    },
    "vi": {
        "breakfast": "Bữa sáng lành mạnh",
        "lunch": "Bữa trưa lành mạnh",
        "dinner": "Bữa tối lành mạnh",
        "snack": "Bữa phụ lành mạnh",
    },
    # Future: Add other languages as needed
    # "es": {"breakfast": "Desayuno saludable", ...},
    # "fr": {"breakfast": "Petit-déjeuner sain", ...},
}


def get_fallback_meal_name(language: str, meal_type: str, index: int) -> str:
    """Get localized fallback meal name.

    Args:
        language: ISO 639-1 language code (e.g., 'en', 'vi')
        meal_type: Meal type ('breakfast', 'lunch', 'dinner', 'snack')
        index: Index number for the fallback (1-based)

    Returns:
        Localized fallback name like "Healthy Breakfast #1"
    """
    # Normalize language code
    lang = language.lower()[:2] if language else "en"

    # Get language-specific names, default to English
    names = FALLBACK_MEAL_NAMES.get(lang, FALLBACK_MEAL_NAMES["en"])

    # Get meal type specific name, default to generic
    base_name = names.get(meal_type.lower(), f"Healthy {meal_type.title()}")

    return f"{base_name} #{index}"
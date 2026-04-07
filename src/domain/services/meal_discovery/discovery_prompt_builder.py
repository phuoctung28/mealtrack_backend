"""
Builds the batch AI prompt for meal discovery generation (NM-67).
Targets 6 lightweight meals per batch for good variety vs speed balance.
"""
from typing import List, Optional

from src.domain.services.prompts.prompt_constants import EMOJI_RULES, LANGUAGE_NAMES

# Cooking time ranges for prompt
COOKING_TIME_MAP = {
    "quick": "under 15 minutes",
    "medium": "15-30 minutes",
    "long": "over 30 minutes",
}

# Calorie level: multiplier applied to remaining_calories, or fixed value
CALORIE_LEVEL_MAP = {
    "snack": 0.15,   # ~200-300 kcal snack
    "light": 0.6,
    "regular": 1.0,
    "hearty": 1.4,
}

# Macro focus prompt instructions
MACRO_FOCUS_MAP = {
    "high_protein": "Prioritize HIGH PROTEIN meals (protein should be 35%+ of calories)",
    "high_carb": "Prioritize HIGH CARB meals (carbs should be 50%+ of calories)",
    "low_fat": "Prioritize LOW FAT meals (fat should be under 20% of calories)",
}


def build_discovery_prompt(
    remaining_calories: float,
    meal_type: Optional[str],
    cuisine_filter: Optional[str],
    cooking_time: Optional[str] = None,
    calorie_level: Optional[str] = None,
    macro_focus: Optional[str] = None,
    exclude_names: List[str] = [],
    allergies: List[str] = [],
    dietary_preferences: List[str] = [],
    disliked_foods: List[str] = [],
    language: str = "en",
) -> str:
    """
    Build a prompt requesting 6 lightweight discovery meals as a JSON array.

    image_search_query is always in English regardless of response language.
    Macros must satisfy: P×4 + C×4 + F×9 ≈ calories ±15%.
    """
    language_name = LANGUAGE_NAMES.get(language, "English")

    # Apply calorie level multiplier
    multiplier = CALORIE_LEVEL_MAP.get(calorie_level, 1.0) if calorie_level else 1.0
    target_cal = max(200, int(remaining_calories * multiplier))

    sections: List[str] = []

    # --- Constraints ---
    if allergies:
        joined = ", ".join(allergies)
        sections.append(f"ALLERGY EXCLUSIONS (STRICT — NEVER INCLUDE): {joined}")

    if dietary_preferences:
        joined = ", ".join(dietary_preferences)
        sections.append(f"Dietary restrictions (STRICT): {joined}")

    if disliked_foods:
        joined = ", ".join(disliked_foods)
        sections.append(f"Foods user dislikes (AVOID if possible): {joined}")

    if exclude_names:
        joined = ", ".join(exclude_names[:40])
        sections.append(f"Already shown — DO NOT repeat: {joined}")

    if meal_type:
        sections.append(f"Meal type: {meal_type}")

    if cuisine_filter:
        sections.append(f"Preferred cuisine: {cuisine_filter}")

    if cooking_time and cooking_time in COOKING_TIME_MAP:
        sections.append(
            f"Cooking time: {COOKING_TIME_MAP[cooking_time]} prep+cook"
        )

    if macro_focus and macro_focus in MACRO_FOCUS_MAP:
        sections.append(MACRO_FOCUS_MAP[macro_focus])

    constraint_block = "\n".join(sections)

    schema = """{
  "meals": [
    {
      "name": "<localized meal name>",
      "name_en": "<English meal name>",
      "emoji": "<single emoji>",
      "cuisine": "<cuisine type>",
      "calories": <integer>,
      "protein": <float grams>,
      "carbs": <float grams>,
      "fat": <float grams>,
      "ingredients": ["ingredient1", "ingredient2"],
      "image_search_query": "<English search phrase for food photo>"
    }
  ]
}"""

    prompt = f"""You are a professional nutritionist. You MUST generate exactly 6 meal options. Not 1, not 3, not 5 — always 6.

TARGET: Each meal should be approximately {target_cal} calories per serving.
LANGUAGE: Return name field in {language_name}. name_en is always English.
CRITICAL: The "meals" array MUST contain exactly 6 items. Fewer is unacceptable.

{constraint_block}

{EMOJI_RULES}

MACRO VALIDATION (MANDATORY):
- Verify each meal: protein×4 + carbs×4 + fat×9 must equal calories ±15%
- If mismatch, recalculate calories from macros before returning

VARIETY REQUIREMENTS:
- Include at least 3 different cuisine types
- Mix breakfast, lunch, dinner appropriate options if no meal_type specified
- Vary protein sources within dietary restrictions (e.g. tofu, tempeh, eggs, cheese, legumes, seitan, paneer for vegetarian)
- Vegetarian does NOT mean vegan — include dairy (cheese, yogurt, cream) and eggs freely

image_search_query rules:
- ALWAYS in English regardless of response language
- 2-4 words describing the dish visually, e.g. "grilled salmon salad"
- Avoid brand names or restaurant names

Return ONLY valid JSON matching this exact schema (no markdown, no explanation):
{schema}"""

    return prompt

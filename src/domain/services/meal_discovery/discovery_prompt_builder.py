"""
Builds the batch AI prompt for meal discovery generation (NM-67).
Targets 15 lightweight meals per batch for good variety vs speed balance.
"""
from typing import List, Optional

from src.domain.services.prompts.prompt_constants import EMOJI_RULES, LANGUAGE_NAMES


def build_discovery_prompt(
    remaining_calories: float,
    meal_type: Optional[str],
    cuisine_filter: Optional[str],
    exclude_names: List[str],
    allergies: List[str],
    dietary_preferences: List[str],
    disliked_foods: List[str],
    language: str = "en",
) -> str:
    """
    Build a prompt requesting 15 lightweight discovery meals as a JSON array.

    image_search_query is always in English regardless of response language.
    Macros must satisfy: P×4 + C×4 + F×9 ≈ calories ±15%.
    """
    language_name = LANGUAGE_NAMES.get(language, "English")
    target_cal = max(200, int(remaining_calories))

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
        joined = ", ".join(exclude_names[:40])  # cap to avoid token bloat
        sections.append(f"Already shown — DO NOT repeat: {joined}")

    if meal_type:
        sections.append(f"Meal type: {meal_type}")

    if cuisine_filter:
        sections.append(f"Preferred cuisine: {cuisine_filter}")

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

    prompt = f"""You are a professional nutritionist. Generate exactly 15 diverse meal options for discovery browsing.

TARGET: Each meal should be approximately {target_cal} calories per serving.
LANGUAGE: Return name field in {language_name}. name_en is always English.

{constraint_block}

{EMOJI_RULES}

MACRO VALIDATION (MANDATORY):
- Verify each meal: protein×4 + carbs×4 + fat×9 must equal calories ±15%
- If mismatch, recalculate calories from macros before returning

VARIETY REQUIREMENTS:
- Include at least 3 different cuisine types
- Mix breakfast, lunch, dinner appropriate options if no meal_type specified
- Vary protein sources (chicken, fish, beef, plant-based, eggs, legumes)
- Include at least 2 vegetarian-friendly options

image_search_query rules:
- ALWAYS in English regardless of response language
- 2-4 words describing the dish visually, e.g. "grilled salmon salad"
- Avoid brand names or restaurant names

Return ONLY valid JSON matching this exact schema (no markdown, no explanation):
{schema}"""

    return prompt

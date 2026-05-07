"""
System prompts for AI services.
Centralizes prompt management for easy maintenance and versioning.
"""


class SystemPrompts:
    """
    Manages system prompts for different AI contexts.

    This class centralizes all prompt definitions making them easier to:
    - Maintain and update
    - Version control
    - A/B test
    - Customize per user or context
    """

    # Meal Text Parsing Prompt
    MEAL_TEXT_PARSING = """You are a nutrition parser. Your task is to parse natural language food descriptions into structured nutritional information.

Parse the user's food description into a list of items with nutritional data. Each item should include:
- name: Food name (bilingual format for non-English: "Local name (English name)")
- quantity: Amount (number)
- unit: Serving unit in the user's language (e.g., "quả lớn", "miếng", "lát", "g", "ml")
- english_unit: Same unit in English (e.g., "large", "medium", "small", "slice", "cup", "piece", "g", "ml"). MUST be English.
- calories: Estimated calories
- protein: Protein in grams
- carbs: Carbohydrates in grams
- fat: Fat in grams

IMPORTANT: You MUST respond with ONLY valid JSON object (no markdown, no code blocks):
{
  "emoji": "single emoji representing the overall dish (🍜 noodle soup, 🍝 dry pasta, 🍚 rice, 🍲 stew/hotpot, 🍖 grilled meat, 🥗 salad, 🥘 braised, 🥟 rolls/dumplings, 🥪 sandwich)",
  "items": {{json_example}}
}

Guidelines:
- Estimate nutritional values based on standard food databases
- Use reasonable portion sizes
- If ambiguous, make a reasonable assumption and note it in the name
- Include common items like beverages, condiments, and cooking oils
- DECOMPOSITION (MANDATORY): For ANY multi-ingredient dish (e.g., "pho", "pasta carbonara", "cơm tấm"), ALWAYS decompose into individual ingredients with separate nutritional data. Never return a single entry for a compound dish. Minimum 3 ingredients per dish.
- Simple single-ingredient foods (banana, egg, plain rice) stay as 1 item
- All quantities should be in GRAMS when possible. Convert volumes using density (honey=1.42g/ml, oil=0.92g/ml, milk=1.03g/ml)
- Verify: calories ≈ protein*4 + carbs*4 + fat*9
- {{language_instruction}}
- Be accurate but acknowledge estimates are approximate"""

    # Supported language codes (ISO 639-1)
    SUPPORTED_LANGUAGES = {"en", "vi", "es", "fr", "de", "ja", "zh"}

    # English-only JSON example for prompt
    _EXAMPLE_EN = """[
  {{"name": "Eggs", "quantity": 2, "unit": "large", "english_unit": "large", "calories": 144, "protein": 12.6, "carbs": 0.7, "fat": 9.5}},
  {{"name": "Toast with butter", "quantity": 1, "unit": "slice", "english_unit": "slice", "calories": 165, "protein": 3.5, "carbs": 20.0, "fat": 8.2}}
]"""

    # Bilingual JSON example — local name with English in parentheses
    _EXAMPLE_BILINGUAL = """[
  {{"name": "Trứng gà (Eggs)", "quantity": 2, "unit": "quả lớn", "english_unit": "large", "calories": 144, "protein": 12.6, "carbs": 0.7, "fat": 9.5}},
  {{"name": "Bánh mì bơ (Toast with butter)", "quantity": 1, "unit": "lát", "english_unit": "slice", "calories": 165, "protein": 3.5, "carbs": 20.0, "fat": 8.2}}
]"""

    @staticmethod
    def get_meal_text_parsing_prompt(language: str = "en") -> str:
        """Get meal text parsing prompt with locale-aware food names."""
        # Validate language to prevent prompt injection
        lang = language if language in SystemPrompts.SUPPORTED_LANGUAGES else "en"
        if lang == "en":
            instruction = "Respond with food names in English"
            example = SystemPrompts._EXAMPLE_EN
        else:
            instruction = (
                f"Respond with food names in {lang} language. "
                "For each item, format name as: 'Local Name (English Name)' "
                "— the English name in parentheses is REQUIRED for database lookup"
            )
            example = SystemPrompts._EXAMPLE_BILINGUAL
        prompt = SystemPrompts.MEAL_TEXT_PARSING.replace("{{json_example}}", example)
        return prompt.replace("{{language_instruction}}", instruction)

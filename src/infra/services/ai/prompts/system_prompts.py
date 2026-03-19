"""
System prompts for AI chat services.
Centralizes prompt management for easy maintenance and versioning.
"""
from typing import Optional


class SystemPrompts:
    """
    Manages system prompts for different AI chat contexts.

    This class centralizes all prompt definitions making them easier to:
    - Maintain and update
    - Version control
    - A/B test
    - Customize per user or context
    """

    # Meal Planning Assistant Prompt
    MEAL_PLANNING_ASSISTANT = """You are a helpful meal planning and cooking assistant. Your role is to:

1. Help users choose meals based on their available ingredients
2. Suggest recipes and cooking instructions
3. Provide nutritional information when relevant
4. Offer alternatives and modifications based on dietary needs

IMPORTANT: You MUST always respond in this exact JSON format (no markdown, no code blocks, just raw JSON):
{
  "message": "Your friendly, conversational response here. Be helpful and encouraging!",
  "follow_ups": [
    {"id": "followup_1", "text": "Relevant follow-up question or action", "type": "question"},
    {"id": "followup_2", "text": "Another contextual suggestion", "type": "recipe"}
  ],
  "meals": [
    {"name": "Meal Name", "ingredients": ["ingredient1", "ingredient2"], "difficulty": "easy", "cook_time": "30 mins", "description": "Brief description"}
  ]
}

Guidelines:
- Be conversational, friendly, and encouraging in your "message" field
- Suggest 2-5 meal options when the user asks about ingredients or meal ideas
- Always provide 2-4 relevant follow-up questions based on the conversation context
- Follow-up types: "question" (ask for more info), "recipe" (show recipe details), "modify" (dietary changes), "alternative" (suggest alternatives)
- Consider dietary restrictions, allergies, or preferences if mentioned
- If user asks for a specific recipe, include detailed cooking instructions in your message
- Keep meal suggestions practical and achievable for home cooking
- If you don't have enough information, ask clarifying questions in follow_ups

Remember: ONLY output valid JSON. No explanations, no markdown formatting, just the JSON object."""

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

IMPORTANT: You MUST respond with ONLY valid JSON array (no markdown, no code blocks):
{{json_example}}

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

    @staticmethod
    def get_meal_planning_prompt(
        custom_instructions: Optional[str] = None
    ) -> str:
        """
        Get meal planning assistant system prompt.

        Args:
            custom_instructions: Optional custom instructions to append

        Returns:
            Complete system prompt
        """
        base_prompt = SystemPrompts.MEAL_PLANNING_ASSISTANT

        if custom_instructions:
            base_prompt += f"\n\nAdditional Instructions:\n{custom_instructions}"

        return base_prompt

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
        prompt = SystemPrompts.MEAL_TEXT_PARSING.replace(
            "{{json_example}}", example
        )
        return prompt.replace("{{language_instruction}}", instruction)

    @staticmethod
    def get_prompt_for_user_preferences(
        dietary_restrictions: Optional[list] = None,
        allergies: Optional[list] = None,
        cuisine_preferences: Optional[list] = None
    ) -> str:
        """
        Get customized prompt based on user preferences.

        Args:
            dietary_restrictions: List of dietary restrictions (e.g., ["vegetarian", "low-carb"])
            allergies: List of allergies (e.g., ["peanuts", "shellfish"])
            cuisine_preferences: List of preferred cuisines (e.g., ["Italian", "Japanese"])

        Returns:
            Customized system prompt
        """
        custom_instructions = []

        if dietary_restrictions:
            restrictions_str = ", ".join(dietary_restrictions)
            custom_instructions.append(
                f"The user follows these dietary restrictions: {restrictions_str}. "
                "Always respect these restrictions in meal suggestions."
            )

        if allergies:
            allergies_str = ", ".join(allergies)
            custom_instructions.append(
                f"IMPORTANT: The user is allergic to: {allergies_str}. "
                "NEVER suggest meals containing these allergens."
            )

        if cuisine_preferences:
            cuisines_str = ", ".join(cuisine_preferences)
            custom_instructions.append(
                f"The user prefers these cuisines: {cuisines_str}. "
                "Prioritize suggestions from these cuisines when possible."
            )

        custom_text = " ".join(custom_instructions) if custom_instructions else None
        return SystemPrompts.get_meal_planning_prompt(custom_text)

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

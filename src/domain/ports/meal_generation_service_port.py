"""
Port for meal generation services following clean architecture.
Single LLM service that handles different prompts and request data.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class MealGenerationServicePort(ABC):
    """Unified port for all meal generation using single LLM with different prompts."""

    @abstractmethod
    def generate_meal_plan(
        self,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: int = None,
        schema: type = None,
        model_purpose: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate meal plan using provided prompt and system message.

        Args:
            prompt: The meal generation prompt
            system_message: System message for the LLM
            response_type: Expected response type ("json" or "text")
            max_tokens: Maximum output tokens
            schema: Optional Pydantic model for structured output
            model_purpose: Optional purpose for rate limit distribution
                          ("meal_names", "recipe_primary", "recipe_secondary")

        Returns:
            Generated meal plan data
        """
        pass

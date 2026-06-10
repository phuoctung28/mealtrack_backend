"""
Port for meal generation services following clean architecture.
Single LLM service that handles different prompts and request data.
"""

from abc import ABC, abstractmethod
from typing import Any


class MealGenerationServicePort(ABC):
    """Unified port for all meal generation using single LLM with different prompts."""

    @abstractmethod
    async def generate_meal_plan_async(
        self,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: int | None = None,
        schema: type | None = None,
        model_purpose: str | None = None,
        thinking_budget: int | None = None,
    ) -> dict[str, Any]:
        """Async version of generate_meal_plan — runs on the caller's event loop.

        Use this from async handlers/services instead of wrapping the sync version
        in asyncio.to_thread(), which causes event-loop mismatch with async-client
        resources (Redis, HTTP) that are bound to the main event loop.
        """

    @abstractmethod
    def generate_meal_plan(
        self,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: int | None = None,
        schema: type | None = None,
        model_purpose: str | None = None,
        thinking_budget: int | None = None,
    ) -> dict[str, Any]:
        """
        Generate meal plan using provided prompt and system message.

        Args:
            prompt: The meal generation prompt
            system_message: System message for the LLM
            response_type: Expected response type ("json" or "text")
            max_tokens: Maximum output tokens
            schema: Optional Pydantic model for structured output
            model_purpose: Optional purpose for rate limit distribution
                          ("meal_names", "discovery", "recipe", "barcode",
                           "parse_text", "general")
            thinking_budget: Optional model thinking budget override

        Returns:
            Generated meal plan data
        """
        pass

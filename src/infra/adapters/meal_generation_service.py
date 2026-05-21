"""
Meal generation service implementation using AI Model Manager.
Provides resilient AI calls with automatic fallback.
"""
import asyncio
import logging
from typing import Any

from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.infra.services.ai.ai_model_manager import AIModelManager, ModelPurpose

logger = logging.getLogger(__name__)

PURPOSE_MAP = {
    "meal_names": ModelPurpose.MEAL_NAMES,
    "recipe":     ModelPurpose.RECIPE,
    "barcode":    ModelPurpose.BARCODE,
    "general":    ModelPurpose.GENERAL,
}


class MealGenerationService(MealGenerationServicePort):
    """
    Unified meal generation service using AIModelManager.
    Provides automatic fallback on provider failures.
    """

    def __init__(self):
        """Initialize with AI model manager."""
        self._ai_manager = AIModelManager.get_instance()

    def generate_meal_plan(
        self,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: int = None,
        schema: type = None,
        model_purpose: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate meal plan with automatic fallback.

        Args:
            prompt: The generation prompt
            system_message: System instructions
            response_type: Response format ("json" or "text")
            max_tokens: Maximum output tokens
            schema: Optional Pydantic model for structured output
            model_purpose: Purpose for model selection

        Returns:
            Generated meal plan data
        """
        purpose = PURPOSE_MAP.get(model_purpose, ModelPurpose.GENERAL)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._ai_manager.generate(
                purpose=purpose,
                prompt=prompt,
                system_message=system_message,
                response_type=response_type,
                max_tokens=max_tokens,
                schema=schema,
            )
        )

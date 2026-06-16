"""
Meal generation service implementation using GeminiService.
Provides resilient AI calls with automatic fallback.
"""

import logging

from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.infra.ai.gemini_service import GeminiService
from src.infra.ai.model_config import ModelPurpose

logger = logging.getLogger(__name__)

PURPOSE_MAP = {
    "meal_names": ModelPurpose.MEAL_NAMES,
    "discovery": ModelPurpose.DISCOVERY,
    "recipe": ModelPurpose.RECIPE,
    "barcode": ModelPurpose.BARCODE,
    "parse_text": ModelPurpose.PARSE_TEXT,
    "general": ModelPurpose.GENERAL,
}


class MealGenerationService(MealGenerationServicePort):
    """
    Unified meal generation service using GeminiService.
    Provides automatic fallback on provider failures.
    """

    def __init__(self):
        """Initialize with GeminiService."""
        self._ai_manager = GeminiService.get_instance()

    async def generate_meal_plan_async(
        self,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: int = None,
        schema: type = None,
        model_purpose: str | None = None,
        thinking_budget: int | None = None,
    ):
        """Generate meal plan — runs directly on the caller's event loop."""
        purpose = PURPOSE_MAP.get(model_purpose, ModelPurpose.GENERAL)
        return await self._ai_manager.text_json(
            purpose=purpose,
            user_prompt=prompt,
            system_prompt=system_message,
            max_tokens=max_tokens,
            schema=schema,
        )

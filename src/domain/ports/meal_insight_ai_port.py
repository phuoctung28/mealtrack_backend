"""Port for AI generation used by meal insight services."""

from abc import ABC, abstractmethod
from typing import Any

from src.domain.model.ai.model_purpose import ModelPurpose


class MealInsightAIPort(ABC):
    """Interface for structured AI generation used by meal value insights."""

    @abstractmethod
    async def generate(
        self,
        *,
        purpose: ModelPurpose,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate a structured response for meal insight copy."""

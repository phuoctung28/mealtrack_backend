"""Abstract interface for AI providers."""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class AICapability(Enum):
    """Capabilities that an AI provider may support."""

    TEXT_GENERATION = "text_generation"
    VISION = "vision"
    STRUCTURED_OUTPUT = "structured_output"


class AIProviderPort(ABC):
    """
    Abstract interface for AI providers.

    Implementations must handle their own authentication and model management.
    The AIModelManager uses this interface to orchestrate multiple providers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider (e.g., 'gemini', 'kimi')."""

    @property
    @abstractmethod
    def supported_capabilities(self) -> Set[AICapability]:
        """Set of capabilities this provider supports."""

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Return list of model identifiers available from this provider."""

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: Optional[int] = None,
        schema: Optional[type] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate text completion.

        Args:
            model: Model identifier
            prompt: User prompt
            system_message: System instructions
            response_type: "json" or "text"
            max_tokens: Maximum output tokens
            schema: Optional Pydantic model for structured output

        Returns:
            Generated content as dictionary

        Raises:
            Exception: On API errors (503, 429, timeout, etc.)
        """

    @abstractmethod
    async def generate_with_vision(
        self,
        model: str,
        prompt: str,
        image_data: bytes,
        system_message: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate completion with image input.

        Args:
            model: Model identifier
            prompt: User prompt
            image_data: Image bytes
            system_message: Optional system instructions

        Returns:
            Generated content as dictionary

        Raises:
            NotImplementedError: If provider doesn't support vision
            Exception: On API errors
        """

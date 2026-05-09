"""Kimi/Moonshot AI provider stub for future implementation."""
import logging
from typing import Any, Dict, List, Optional, Set

from src.domain.ports.ai_provider_port import AICapability, AIProviderPort

logger = logging.getLogger(__name__)


class KimiProvider(AIProviderPort):
    """
    Kimi/Moonshot AI provider stub.

    Not yet implemented - requires Tier 1 upgrade for sufficient RPM.
    Current Tier 0 has ~3 RPM which is insufficient for fallback traffic.
    """

    AVAILABLE_MODELS = ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]

    @property
    def provider_name(self) -> str:
        return "kimi"

    @property
    def supported_capabilities(self) -> Set[AICapability]:
        return {AICapability.TEXT_GENERATION}

    def get_available_models(self) -> List[str]:
        return self.AVAILABLE_MODELS.copy()

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
        """Not yet implemented."""
        raise NotImplementedError(
            "Kimi provider not yet implemented. "
            "Requires Tier 1 upgrade for sufficient RPM (current: ~3 RPM, needed: 200+ RPM)"
        )

    async def generate_with_vision(
        self,
        model: str,
        prompt: str,
        image_data: bytes,
        system_message: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Kimi does not support vision."""
        raise NotImplementedError("Kimi provider does not support vision capabilities")

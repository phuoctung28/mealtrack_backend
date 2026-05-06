"""Provider-agnostic AI model manager with fallback support."""
import logging
import threading
from enum import Enum
from typing import Any, Dict, List, Optional

from src.domain.exceptions.ai_exceptions import AIUnavailableError
from src.domain.ports.ai_provider_port import AICapability
from src.infra.services.ai.provider_circuit_breaker import (
    CircuitState,
    ProviderCircuitBreaker,
)
from src.infra.services.ai.providers.gemini_provider import GeminiProvider
from src.infra.services.ai.providers.mistral_provider import MistralProvider

logger = logging.getLogger(__name__)


class ModelPurpose(Enum):
    """Purpose-based model selection."""

    MEAL_SCAN = "meal_scan"
    INGREDIENT_SCAN = "ingredient_scan"
    PARSE_TEXT = "parse_text"
    BARCODE = "barcode"
    MEAL_NAMES = "meal_names"
    RECIPE_PRIMARY = "recipe_primary"
    RECIPE_SECONDARY = "recipe_secondary"
    DISCOVERY = "discovery"
    GENERAL = "general"


FALLBACK_CHAINS: Dict[ModelPurpose, List[str]] = {
    # Critical paths: Gemini flash → flash-lite → Mistral
    ModelPurpose.MEAL_SCAN: ["gemini-2.5-flash", "gemini-2.5-flash-lite", "pixtral-12b-2409"],
    ModelPurpose.INGREDIENT_SCAN: ["gemini-2.5-flash-lite", "gemini-2.5-flash", "pixtral-12b-2409"],
    # Text generation: Gemini → Mistral small (fast, cheap)
    ModelPurpose.PARSE_TEXT: ["gemini-2.5-flash-lite", "gemini-2.5-flash", "mistral-small-latest"],
    ModelPurpose.BARCODE: ["gemini-2.5-flash-lite", "gemini-2.5-flash", "mistral-small-latest"],
    ModelPurpose.MEAL_NAMES: ["gemini-2.5-flash-lite", "gemini-2.5-flash", "mistral-small-latest"],
    # Recipe generation: Gemini → Mistral large (more capable)
    ModelPurpose.RECIPE_PRIMARY: ["gemini-2.5-flash", "gemini-2.5-flash-lite", "mistral-large-latest"],
    ModelPurpose.RECIPE_SECONDARY: ["gemini-2.5-flash-lite", "gemini-2.5-flash", "mistral-large-latest"],
    ModelPurpose.DISCOVERY: ["gemini-2.5-flash-lite", "gemini-2.5-flash", "mistral-small-latest"],
    ModelPurpose.GENERAL: ["gemini-2.5-flash", "gemini-2.5-flash-lite", "mistral-small-latest"],
}


class AIModelManager:
    """
    Provider-agnostic AI model manager.

    Coordinates multiple providers through AIProviderPort interface.
    Uses circuit breaker for health tracking and automatic fallback.
    """

    _instance: Optional["AIModelManager"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "AIModelManager":
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton for testing."""
        with cls._lock:
            cls._instance = None

    def __init__(self) -> None:
        self._circuit_breaker = ProviderCircuitBreaker()
        self._gemini = GeminiProvider()
        self._mistral = MistralProvider()
        self._providers = {
            "gemini": self._gemini,
            "mistral": self._mistral,
        }

        # Log provider availability
        if self._mistral.is_available():
            logger.info("[AI-MANAGER] Mistral provider available as fallback")
        else:
            logger.warning("[AI-MANAGER] Mistral provider not configured (MISTRAL_API_KEY missing)")

    def get_fallback_chain(self, purpose: ModelPurpose) -> List[str]:
        """Get fallback chain for a purpose."""
        return FALLBACK_CHAINS.get(purpose, FALLBACK_CHAINS[ModelPurpose.GENERAL]).copy()

    def _get_provider_for_model(self, model: str):
        """Get provider that owns a model."""
        if model.startswith("gemini"):
            return self._gemini
        if model.startswith("mistral") or model.startswith("pixtral"):
            if self._mistral.is_available():
                return self._mistral
            logger.debug(f"[SKIP-MISTRAL] model={model} | reason=not configured")
            return None
        return None

    async def generate(
        self,
        purpose: ModelPurpose,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: Optional[int] = None,
        schema: Optional[type] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate with automatic fallback.

        Tries each model in the fallback chain until one succeeds.
        Records failures/successes in circuit breaker.
        """
        chain = self.get_fallback_chain(purpose)
        available = self._circuit_breaker.filter_available(chain)

        if not available:
            logger.warning(f"[ALL-CIRCUITS-OPEN] purpose={purpose.value} | forcing first model")
            available = [chain[0]]

        attempted = []
        last_error = None

        for model in available:
            provider = self._get_provider_for_model(model)
            if provider is None:
                continue

            attempted.append(model)

            try:
                logger.debug(f"[AI-ATTEMPT] purpose={purpose.value} | model={model}")

                result = await provider.generate(
                    model=model,
                    prompt=prompt,
                    system_message=system_message,
                    response_type=response_type,
                    max_tokens=max_tokens,
                    schema=schema,
                    **kwargs,
                )

                self._circuit_breaker.record_success(model)

                if model != chain[0]:
                    logger.info(
                        f"[AI-FALLBACK-SUCCESS] purpose={purpose.value} | "
                        f"failed={attempted[:-1]} | succeeded={model}"
                    )

                return result

            except Exception as e:
                last_error = str(e)
                error_code = provider.extract_error_code(e)

                if self._circuit_breaker.should_trip(error_code):
                    self._circuit_breaker.record_failure(model)

                logger.warning(
                    f"[AI-ATTEMPT-FAILED] purpose={purpose.value} | "
                    f"model={model} | error={last_error[:100]}"
                )

        raise AIUnavailableError(
            f"All models failed for {purpose.value}",
            attempted_models=attempted,
            last_error=last_error,
        )

    async def generate_with_vision(
        self,
        purpose: ModelPurpose,
        prompt: str,
        image_data: bytes,
        system_message: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate with vision, with automatic fallback."""
        chain = self.get_fallback_chain(purpose)
        available = self._circuit_breaker.filter_available(chain)

        if not available:
            available = [chain[0]]

        attempted = []
        last_error = None

        for model in available:
            provider = self._get_provider_for_model(model)
            if provider is None:
                continue

            if AICapability.VISION not in provider.supported_capabilities:
                continue

            attempted.append(model)

            try:
                result = await provider.generate_with_vision(
                    model=model,
                    prompt=prompt,
                    image_data=image_data,
                    system_message=system_message,
                    **kwargs,
                )

                self._circuit_breaker.record_success(model)
                return result

            except Exception as e:
                last_error = str(e)
                error_code = provider.extract_error_code(e)

                if self._circuit_breaker.should_trip(error_code):
                    self._circuit_breaker.record_failure(model)

        raise AIUnavailableError(
            f"All vision models failed for {purpose.value}",
            attempted_models=attempted,
            last_error=last_error,
        )

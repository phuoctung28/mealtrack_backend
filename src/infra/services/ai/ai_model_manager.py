"""Provider-agnostic AI model manager with fallback support."""

import logging
import threading
from enum import Enum
from typing import Any, Optional

from src.domain.exceptions.ai_exceptions import AIUnavailableError
from src.domain.ports.ai_provider_port import AICapability
from src.observability import log_event
from src.infra.services.ai.provider_circuit_breaker import (
    ProviderCircuitBreaker,
)
from src.infra.services.ai.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class ModelPurpose(Enum):
    """Purpose-based model selection."""

    MEAL_SCAN = "meal_scan"
    INGREDIENT_SCAN = "ingredient_scan"
    PARSE_TEXT = "parse_text"
    BARCODE = "barcode"
    MEAL_NAMES = "meal_names"
    RECIPE = "recipe"
    DISCOVERY = "discovery"
    GENERAL = "general"


FALLBACK_CHAINS: dict[ModelPurpose, list[str]] = {
    # ==========================================================================
    # VISION / SHORT STRUCTURED TASKS: Gemini Flash-Lite first → Flash fallback
    # ==========================================================================
    ModelPurpose.MEAL_SCAN: ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    ModelPurpose.INGREDIENT_SCAN: ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    # ==========================================================================
    # SHORT STRUCTURED TEXT: Gemini Flash-Lite first → Flash fallback
    # ==========================================================================
    ModelPurpose.PARSE_TEXT: [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ],
    ModelPurpose.BARCODE: ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    ModelPurpose.MEAL_NAMES: [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ],
    ModelPurpose.DISCOVERY: [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ],
    ModelPurpose.GENERAL: ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    # ==========================================================================
    # RECIPE TASKS: Gemini Flash-Lite first → Flash fallback
    # ==========================================================================
    ModelPurpose.RECIPE: [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ],
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
        self._cache_manager: Any | None = None
        self._circuit_breaker = ProviderCircuitBreaker()
        self._gemini = GeminiProvider()
        self._providers = {"gemini": self._gemini}

    def set_cache_manager(self, cache_manager) -> None:
        """Wire in GeminiCacheManager after startup warmup."""
        self._cache_manager = cache_manager

    def get_fallback_chain(self, purpose: ModelPurpose) -> list[str]:
        """Get fallback chain for a purpose."""
        return FALLBACK_CHAINS.get(
            purpose, FALLBACK_CHAINS[ModelPurpose.GENERAL]
        ).copy()

    def _get_provider_for_model(self, model: str):
        """Get provider that owns a model."""
        if model.startswith("gemini"):
            return self._gemini
        return None

    async def generate(
        self,
        purpose: ModelPurpose,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: int | None = None,
        schema: type | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate with automatic fallback.

        Tries each model in the fallback chain until one succeeds.
        Records failures/successes in circuit breaker.
        """
        chain = self.get_fallback_chain(purpose)
        available = self._circuit_breaker.filter_available(chain)

        if not available:
            logger.warning(
                f"[ALL-CIRCUITS-OPEN] purpose={purpose.value} | forcing first model"
            )
            available = [chain[0]]

        # Gemini context caches are model-specific; lookup happens per attempt.
        cache_type: str | None = None
        if self._cache_manager is not None:
            purpose_to_cache_type = {
                ModelPurpose.RECIPE: "recipe",
                ModelPurpose.MEAL_SCAN: "vision",
                ModelPurpose.PARSE_TEXT: "text_parse",
                ModelPurpose.BARCODE: "text_parse",
            }
            cache_type = purpose_to_cache_type.get(purpose)

        attempted = []
        last_error = None

        for model in available:
            provider = self._get_provider_for_model(model)
            if provider is None:
                continue

            attempted.append(model)

            try:
                logger.debug(f"[AI-ATTEMPT] purpose={purpose.value} | model={model}")
                cache_name = await self._get_cache_name_for_model(cache_type, model)

                result = await provider.generate(
                    model=model,
                    prompt=prompt,
                    system_message=system_message,
                    response_type=response_type,
                    max_tokens=max_tokens,
                    schema=schema,
                    purpose_hint=purpose.value,  # NEW: pass real purpose to provider
                    cache_name=cache_name if model.startswith("gemini") else None,
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

        log_event("warning", "ai.provider.failure", attributes={"component": "ai_model_manager", "attempt_count": len(attempted)})
        raise AIUnavailableError(
            f"All models failed for {purpose.value}",
            attempted_models=attempted,
            last_error=last_error,
        )

    async def _get_cache_name_for_model(
        self, cache_type: str | None, model: str
    ) -> str | None:
        """Return Gemini cache only when cache metadata matches the attempted model."""
        if (
            cache_type is None
            or self._cache_manager is None
            or not model.startswith("gemini")
        ):
            return None
        try:
            if hasattr(self._cache_manager, "get_cache_name_for_model"):
                return await self._cache_manager.get_cache_name_for_model(
                    cache_type, model
                )
            return None
        except Exception as e:
            logger.warning("[AI-CACHE-LOOKUP-FAILED] cache_type=%s error=%s", cache_type, e)
            return None

    async def generate_with_vision(
        self,
        purpose: ModelPurpose,
        prompt: str,
        image_data: bytes,
        system_message: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
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
                    purpose_hint=purpose.value,  # NEW
                    **kwargs,
                )

                self._circuit_breaker.record_success(model)
                return result

            except Exception as e:
                last_error = str(e)
                error_code = provider.extract_error_code(e)

                if self._circuit_breaker.should_trip(error_code):
                    self._circuit_breaker.record_failure(model)

        log_event("warning", "ai.provider.failure", attributes={"component": "ai_model_manager", "attempt_count": len(attempted)})
        raise AIUnavailableError(
            f"All vision models failed for {purpose.value}",
            attempted_models=attempted,
            last_error=last_error,
        )

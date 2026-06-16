"""
Single-entrypoint Gemini service replacing AIModelManager + GeminiModelManager + GeminiProvider.

Exposes two async methods:
  vision()    — image + prompt → dict
  text_json() — prompt + system → dict

Internally manages: LangChain model pool, circuit breaker, context cache, fallback chain.
"""

import asyncio
import base64
import logging
import os
import re
import threading
import time
from typing import Any, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import ValidationError

from src.domain.exceptions.ai_exceptions import (
    AIOutputValidationError,
    AIUnavailableError,
)
from src.domain.services.ai_output_validation_service import summarize_validation_error
from src.infra.ai.circuit_breaker import ProviderCircuitBreaker
from src.infra.ai.json_extract import extract_json as extract_ai_json
from src.infra.ai.model_config import (
    FALLBACK_CHAINS,
    NO_THINKING_PURPOSES,
    PURPOSE_TEMPERATURES,
    ModelPurpose,
)
from src.infra.services.ai.gemini_cache_handler import (
    check_memory_and_evict,
    clear_cache,
    evict_expired,
    evict_lru,
)
from src.infra.services.ai.gemini_model_config import (
    DEFAULT_MAX_CACHE_SIZE,
    DEFAULT_TTL_SECONDS,
    MEMORY_WARNING_THRESHOLD_MB,
    CachedModel,
)
from src.observability import log_event

logger = logging.getLogger(__name__)

# Purpose → cache_type string used by GeminiCacheManager
_PURPOSE_TO_CACHE_TYPE: dict[ModelPurpose, str] = {
    ModelPurpose.RECIPE: "recipe",
    ModelPurpose.MEAL_SCAN: "vision",
    ModelPurpose.PARSE_TEXT: "text_parse",
    ModelPurpose.BARCODE: "text_parse",
}


class GeminiService:
    """
    Consolidated Gemini AI service — singleton.

    Replaces AIModelManager + GeminiModelManager + GeminiProvider.
    VisionAIService and MealGenerationService use this internally.
    """

    _instance: Optional["GeminiService"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "GeminiService":
        """Get singleton instance, creating it on first call."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton — for testing only."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._clear_model_pool()
            cls._instance = None

    def __init__(self) -> None:
        self._api_key: str = os.environ.get("GOOGLE_API_KEY", "")
        if not self._api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        self._request_timeout: float = float(
            os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "15")
        )
        self._max_retries: int = int(os.getenv("GEMINI_MAX_RETRIES", "1"))

        # Model pool (TTL+LRU cache of ChatGoogleGenerativeAI instances)
        self._models: dict[str, CachedModel] = {}
        self._model_lock = threading.Lock()
        self._max_pool_size: int = int(
            os.getenv("GEMINI_MAX_CACHE_SIZE", DEFAULT_MAX_CACHE_SIZE)
        )
        self._pool_ttl: int = int(os.getenv("GEMINI_CACHE_TTL", DEFAULT_TTL_SECONDS))
        self._memory_threshold_mb: int = int(
            os.getenv("MEMORY_WARNING_THRESHOLD_MB", MEMORY_WARNING_THRESHOLD_MB)
        )

        self._circuit_breaker = ProviderCircuitBreaker()
        self._cache_manager: Any | None = None

    # ------------------------------------------------------------------
    # Public wiring
    # ------------------------------------------------------------------

    def set_cache_manager(self, cache_manager: Any) -> None:
        """Wire in GeminiCacheManager after startup warmup."""
        self._cache_manager = cache_manager

    def get_fallback_chain(self, purpose: ModelPurpose) -> list[str]:
        """Return a copy of the fallback chain for a purpose."""
        return FALLBACK_CHAINS.get(purpose, FALLBACK_CHAINS[ModelPurpose.GENERAL]).copy()

    # ------------------------------------------------------------------
    # Public async methods
    # ------------------------------------------------------------------

    async def vision(
        self,
        purpose: ModelPurpose,
        image_bytes: bytes,
        prompt: str,
        system_prompt: str | None = None,
        schema: type | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """
        Vision inference with automatic fallback.

        Args:
            purpose:      ModelPurpose enum — selects model chain.
            image_bytes:  Raw image bytes (JPEG/PNG/WebP).
            prompt:       User-facing prompt text.
            system_prompt: Optional system instruction.
            schema:       Optional Pydantic model for structured output.
            max_tokens:   Optional max output tokens override.

        Returns:
            Parsed dict from AI response.

        Raises:
            AIOutputValidationError: Structured output failed validation.
            AIUnavailableError:      All models in chain failed.
        """
        chain = self.get_fallback_chain(purpose)
        available = self._circuit_breaker.filter_available(chain)
        if not available:
            available = [chain[0]]

        attempted: list[str] = []
        last_error: str | None = None
        primary_model = chain[0]

        for model in available:
            attempted.append(model)
            t0 = time.perf_counter()
            try:
                result = await self._call_vision(
                    model=model,
                    prompt=prompt,
                    image_bytes=image_bytes,
                    system_prompt=system_prompt,
                    schema=schema,
                    max_tokens=max_tokens,
                    purpose_hint=purpose.value,
                )
                latency_ms = int((time.perf_counter() - t0) * 1000)
                self._circuit_breaker.record_success(model)
                from src.domain.services.prompts.system_prompts import SystemPrompts  # lazy import avoids circular dep
                logger.info(
                    "[AI-CALL] purpose=%s model=%s prompt_version=%s latency_ms=%d retry_count=%d fallback_used=%s",
                    purpose.value,
                    model,
                    SystemPrompts.PROMPT_VERSION,
                    latency_ms,
                    len(attempted) - 1,
                    model != primary_model,
                )
                return result

            except AIOutputValidationError:
                raise
            except Exception as exc:
                last_error = str(exc)
                error_code = self._extract_error_code(exc)
                if self._circuit_breaker.should_trip(error_code):
                    self._circuit_breaker.record_failure(model)
                logger.warning(
                    "[AI-VISION-FAILED] purpose=%s model=%s error=%s",
                    purpose.value,
                    model,
                    last_error[:100],
                )

        log_event(
            "warning",
            "ai.provider.failure",
            attributes={"component": "gemini_service", "attempt_count": len(attempted)},
        )
        raise AIUnavailableError(
            f"All vision models failed for {purpose.value}",
            attempted_models=attempted,
            last_error=last_error,
        )

    async def text_json(
        self,
        purpose: ModelPurpose,
        user_prompt: str,
        system_prompt: str,
        schema: type | None = None,
        max_tokens: int | None = None,
        cache_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Text-to-JSON inference with automatic fallback.

        Args:
            purpose:      ModelPurpose enum — selects model chain.
            user_prompt:  User-facing prompt.
            system_prompt: System instruction (may be in Gemini context cache).
            schema:       Optional Pydantic model for structured output.
            max_tokens:   Optional max output tokens override.
            cache_name:   Optional Gemini context cache name (overrides auto-lookup).

        Returns:
            Parsed dict from AI response.

        Raises:
            AIOutputValidationError: Structured output failed validation.
            AIUnavailableError:      All models in chain failed.
        """
        chain = self.get_fallback_chain(purpose)
        available = self._circuit_breaker.filter_available(chain)
        if not available:
            logger.warning(
                "[ALL-CIRCUITS-OPEN] purpose=%s | forcing first model", purpose.value
            )
            available = [chain[0]]

        cache_type: str | None = _PURPOSE_TO_CACHE_TYPE.get(purpose)
        attempted: list[str] = []
        last_error: str | None = None
        primary_model = chain[0]

        for model in available:
            attempted.append(model)
            t0 = time.perf_counter()
            try:
                logger.debug("[AI-ATTEMPT] purpose=%s model=%s", purpose.value, model)
                resolved_cache = cache_name or await self._resolve_cache_name(
                    cache_type, model
                )
                result = await self._call_text(
                    model=model,
                    user_prompt=user_prompt,
                    system_prompt=system_prompt,
                    schema=schema,
                    max_tokens=max_tokens,
                    cache_name=resolved_cache,
                    purpose_hint=purpose.value,
                )
                latency_ms = int((time.perf_counter() - t0) * 1000)
                self._circuit_breaker.record_success(model)

                fallback_used = model != primary_model
                if fallback_used:
                    logger.info(
                        "[AI-FALLBACK-SUCCESS] purpose=%s failed=%s succeeded=%s",
                        purpose.value,
                        attempted[:-1],
                        model,
                    )
                from src.domain.services.prompts.system_prompts import SystemPrompts  # lazy import avoids circular dep
                logger.info(
                    "[AI-CALL] purpose=%s model=%s prompt_version=%s latency_ms=%d retry_count=%d fallback_used=%s",
                    purpose.value,
                    model,
                    SystemPrompts.PROMPT_VERSION,
                    latency_ms,
                    len(attempted) - 1,
                    fallback_used,
                )
                return result

            except AIOutputValidationError:
                raise
            except Exception as exc:
                last_error = str(exc)
                error_code = self._extract_error_code(exc)
                if self._circuit_breaker.should_trip(error_code):
                    self._circuit_breaker.record_failure(model)
                logger.warning(
                    "[AI-ATTEMPT-FAILED] purpose=%s model=%s error=%s",
                    purpose.value,
                    model,
                    last_error[:100],
                )

        log_event(
            "warning",
            "ai.provider.failure",
            attributes={"component": "gemini_service", "attempt_count": len(attempted)},
        )
        raise AIUnavailableError(
            f"All models failed for {purpose.value}",
            attempted_models=attempted,
            last_error=last_error,
        )

    # ------------------------------------------------------------------
    # Internal: LangChain invocation
    # ------------------------------------------------------------------

    async def _call_vision(
        self,
        model: str,
        prompt: str,
        image_bytes: bytes,
        system_prompt: str | None,
        schema: type | None,
        max_tokens: int | None,
        purpose_hint: str,
    ) -> dict[str, Any]:
        llm = self._get_model(
            model_name=model,
            purpose_hint=purpose_hint,
            max_output_tokens=max_tokens or 4096,
        )

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:image/jpeg;base64,{image_b64}"

        messages: list[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]
            )
        )

        if schema:
            llm_structured = llm.with_structured_output(schema, include_raw=True)
            try:
                result = await asyncio.to_thread(llm_structured.invoke, messages)
            except (ValueError, ValidationError) as exc:
                raise AIOutputValidationError(
                    "Invalid AI structured output",
                    purpose=purpose_hint,
                    attempt_count=1,
                    validation_details=summarize_validation_error(exc),
                ) from exc
            parsed = result.get("parsed") if isinstance(result, dict) else result
            if parsed is None:
                raise AIOutputValidationError(
                    "Invalid AI structured output",
                    purpose=purpose_hint,
                    attempt_count=1,
                    validation_details=["structured vision output returned empty result"],
                )
            if hasattr(parsed, "model_dump"):
                return parsed.model_dump()
            return dict(parsed)

        response = await asyncio.to_thread(llm.invoke, messages)
        return extract_ai_json(response.content)

    async def _call_text(
        self,
        model: str,
        user_prompt: str,
        system_prompt: str,
        schema: type | None,
        max_tokens: int | None,
        cache_name: str | None,
        purpose_hint: str,
    ) -> dict[str, Any]:
        extra_kwargs: dict[str, Any] = {}
        if cache_name:
            extra_kwargs["cached_content"] = cache_name

        response_mime_type: str | None = None
        if not schema:
            response_mime_type = "application/json"

        llm = self._get_model(
            model_name=model,
            purpose_hint=purpose_hint,
            max_output_tokens=max_tokens,
            response_mime_type=response_mime_type,
            **extra_kwargs,
        )

        # When cache is active, system message is already in it — omit to avoid 400
        messages: list[BaseMessage] = []
        if not cache_name and system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=user_prompt))

        if schema:
            llm_structured = llm.with_structured_output(schema, include_raw=True)
            try:
                result = await asyncio.to_thread(llm_structured.invoke, messages)
            except (ValueError, ValidationError) as exc:
                raise AIOutputValidationError(
                    "Invalid AI structured output",
                    purpose=purpose_hint,
                    attempt_count=1,
                    validation_details=summarize_validation_error(exc),
                ) from exc
            parsed = result.get("parsed") if isinstance(result, dict) else result
            if parsed is None:
                raise AIOutputValidationError(
                    "Invalid AI structured output",
                    purpose=purpose_hint,
                    attempt_count=1,
                    validation_details=["structured output returned empty result"],
                )
            if hasattr(parsed, "model_dump"):
                return parsed.model_dump()
            return dict(parsed)

        response = await asyncio.to_thread(llm.invoke, messages)
        return extract_ai_json(response.content)

    # ------------------------------------------------------------------
    # Internal: model pool
    # ------------------------------------------------------------------

    def _get_model(
        self,
        model_name: str,
        purpose_hint: str,
        max_output_tokens: int | None = None,
        response_mime_type: str | None = None,
        **extra_kwargs: Any,
    ):
        """Get or create a pooled ChatGoogleGenerativeAI instance."""
        from langchain_google_genai import ChatGoogleGenerativeAI

        purpose = _hint_to_purpose(purpose_hint)
        temperature = PURPOSE_TEMPERATURES.get(purpose, 0.2)

        kwargs: dict[str, Any] = {}
        if purpose in NO_THINKING_PURPOSES:
            kwargs["thinking_budget"] = 0
        kwargs.update(extra_kwargs)

        config_key = _make_pool_key(
            model_name, temperature, max_output_tokens, response_mime_type, **kwargs
        )

        with self._model_lock:
            check_memory_and_evict(self._models, self._memory_threshold_mb)
            evict_expired(self._models, self._pool_ttl)

            if config_key in self._models:
                cached = self._models[config_key]
                if not cached.is_expired(self._pool_ttl):
                    cached.touch()
                    return cached.model
                del self._models[config_key]

            if len(self._models) >= self._max_pool_size:
                evict_lru(self._models)

            cfg: dict[str, Any] = {
                "model": model_name,
                "temperature": temperature,
                "google_api_key": self._api_key,
                "convert_system_message_to_human": True,
                "request_timeout": self._request_timeout,
                "retries": self._max_retries,
            }
            if max_output_tokens is not None:
                cfg["max_output_tokens"] = max_output_tokens
            if response_mime_type is not None:
                cfg["response_mime_type"] = response_mime_type
            cfg.update(
                {
                    k: v
                    for k, v in kwargs.items()
                    if k not in ("google_api_key", "model")
                }
            )

            model = ChatGoogleGenerativeAI(**cfg)
            self._models[config_key] = CachedModel(model=model)
            logger.info(
                "[GEMINI-POOL] created model=%s config=%s pool_size=%d/%d",
                model_name,
                config_key,
                len(self._models),
                self._max_pool_size,
            )
            return model

    def _clear_model_pool(self) -> int:
        """Clear all pooled model instances. Returns count cleared."""
        with self._model_lock:
            return clear_cache(self._models)

    # ------------------------------------------------------------------
    # Internal: context cache lookup
    # ------------------------------------------------------------------

    async def _resolve_cache_name(
        self, cache_type: str | None, model: str
    ) -> str | None:
        """Look up Gemini context cache name only when it matches the attempted model."""
        if cache_type is None or self._cache_manager is None:
            return None
        try:
            if hasattr(self._cache_manager, "get_cache_name_for_model"):
                return await self._cache_manager.get_cache_name_for_model(
                    cache_type, model
                )
        except Exception as exc:
            logger.warning(
                "[AI-CACHE-LOOKUP-FAILED] cache_type=%s error=%s", cache_type, exc
            )
        return None

    # ------------------------------------------------------------------
    # Internal: error code extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_error_code(error: Exception) -> int | str | None:
        """Extract HTTP status code or error type string from exception."""
        error_str = str(error)
        code_match = re.search(r"\b(503|429|500|502|504)\b", error_str)
        if code_match:
            return int(code_match.group(1))
        if "timeout" in error_str.lower():
            return "timeout"
        return None


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _hint_to_purpose(hint: str) -> ModelPurpose:
    """Map a purpose_hint string back to ModelPurpose enum."""
    try:
        return ModelPurpose(hint)
    except ValueError:
        return ModelPurpose.GENERAL


def _make_pool_key(
    model_name: str,
    temperature: float,
    max_output_tokens: int | None,
    response_mime_type: str | None,
    **kwargs: Any,
) -> str:
    """Build a deterministic cache key from model configuration."""
    skip = {"google_api_key", "model", "convert_system_message_to_human"}
    parts = [
        f"model={model_name}",
        f"temp={temperature:.1f}",
        f"max_tokens={max_output_tokens}",
        f"mime={response_mime_type}",
    ]
    parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()) if k not in skip)
    return "|".join(parts)

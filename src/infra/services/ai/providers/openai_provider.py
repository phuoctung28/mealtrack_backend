"""OpenAI implementation of AIProviderPort using LangChain OpenAI adapter."""

from __future__ import annotations

import re
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)
from pydantic import ValidationError

from src.domain.ports.ai_provider_port import AICapability, AIProviderPort
from src.infra.adapters.ai_json_utils import extract_json as extract_ai_json
from src.infra.services.ai.ai_vision_errors import AIVisionError, AIVisionFailureKind
from src.infra.services.ai.langchain_openai_adapter import OpenAILangChainAdapter
from src.infra.services.ai.openai_prompt_cache_policy import OpenAIPromptCachePolicy
from src.observability import increment_metric


class OpenAIProvider(AIProviderPort):
    """OpenAI provider for text, vision, and structured output."""

    def __init__(
        self,
        *,
        api_key: str,
        request_timeout_seconds: int,
        max_retries: int,
        store_responses: bool,
        prompt_cache_enabled: bool = True,
        prompt_cache_retention: str | None = None,
        prompt_cache_key_prefix: str = "mealtrack",
    ) -> None:
        self._langchain = OpenAILangChainAdapter(
            api_key=api_key,
            request_timeout_seconds=request_timeout_seconds,
            max_retries=max_retries,
            store_responses=store_responses,
        )
        self._prompt_cache_policy = OpenAIPromptCachePolicy(
            enabled=prompt_cache_enabled,
            key_prefix=prompt_cache_key_prefix,
            retention=prompt_cache_retention,
        )

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def supported_capabilities(self) -> set[AICapability]:
        return {
            AICapability.TEXT_GENERATION,
            AICapability.VISION,
            AICapability.STRUCTURED_OUTPUT,
        }

    def get_available_models(self) -> list[str]:
        return []

    def _prompt_cache_kwargs(
        self,
        *,
        model: str,
        purpose_hint: str | None,
        system_message: str | None,
    ) -> dict[str, Any]:
        return self._prompt_cache_policy.request_kwargs(
            model=model,
            purpose_hint=purpose_hint,
            system_message=system_message,
        )

    def _record_prompt_cache_usage(
        self,
        raw_message: Any,
        *,
        model: str,
        purpose_hint: str | None,
    ) -> None:
        input_tokens = self._langchain.input_tokens(raw_message)
        cached_tokens = self._langchain.cached_tokens(raw_message)
        attributes = {
            "ai_provider": "openai",
            "ai_model": model,
            "ai_purpose": purpose_hint or "unknown",
            "cache_hit": "true" if cached_tokens > 0 else "false",
        }
        increment_metric(
            "ai.openai.prompt_cache.request.count",
            attributes=attributes,
        )
        increment_metric(
            "ai.openai.prompt_cache.cached_tokens",
            cached_tokens,
            unit="token",
            attributes=attributes,
        )
        if input_tokens > 0:
            increment_metric(
                "ai.openai.prompt_cache.input_tokens",
                input_tokens,
                unit="token",
                attributes=attributes,
            )

    async def generate(
        self,
        model: str,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: int | None = None,
        schema: type | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        purpose_hint = kwargs.get("purpose_hint")
        prompt_cache_kwargs = self._prompt_cache_kwargs(
            model=model,
            purpose_hint=purpose_hint,
            system_message=system_message,
        )
        if schema is not None:
            result = await self._langchain.generate_structured(
                model=model,
                prompt=prompt,
                system_message=system_message,
                schema=schema,
                max_tokens=max_tokens,
                request_kwargs=prompt_cache_kwargs,
            )
            self._record_prompt_cache_usage(
                result.raw_message,
                model=model,
                purpose_hint=purpose_hint,
            )
            return self._dump_parsed(result.parsed)

        result = await self._langchain.generate_raw(
            model=model,
            prompt=prompt,
            system_message=system_message,
            max_tokens=max_tokens,
            request_kwargs=prompt_cache_kwargs,
        )
        self._record_prompt_cache_usage(
            result.raw_message,
            model=model,
            purpose_hint=purpose_hint,
        )
        if response_type == "json":
            raw_content = result.parsed.get("raw_content", "")
            return extract_ai_json(raw_content)
        return self._dump_parsed(result.parsed)

    async def generate_with_vision(
        self,
        model: str,
        prompt: str,
        image_data: bytes,
        system_message: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        schema = kwargs["schema"]
        max_tokens: int | None = kwargs.get("max_tokens")
        image_mime_type = kwargs.get("image_mime_type", "image/jpeg")
        purpose_hint = kwargs.get("purpose_hint")
        prompt_cache_kwargs = self._prompt_cache_kwargs(
            model=model,
            purpose_hint=purpose_hint,
            system_message=system_message,
        )

        try:
            result = await self._langchain.generate_vision_structured(
                model=model,
                prompt=prompt,
                image_data=image_data,
                image_mime_type=image_mime_type,
                system_message=system_message,
                schema=schema,
                max_tokens=max_tokens,
                request_kwargs=prompt_cache_kwargs,
            )
        except ValidationError as exc:
            raise AIVisionError(
                f"[OPENAI-VISION-SCHEMA-FAIL] provider=openai model={model}",
                kind=AIVisionFailureKind.schema_validation,
                provider="openai",
                model=model,
            ) from exc
        self._record_prompt_cache_usage(
            result.raw_message,
            model=model,
            purpose_hint=purpose_hint,
        )
        return self._dump_parsed(result.parsed)

    def extract_error_code(self, error: Exception) -> int | str | None:
        if isinstance(error, RateLimitError):
            return 429
        if isinstance(error, APITimeoutError):
            return "timeout"
        if isinstance(error, APIConnectionError):
            return "connection"
        if isinstance(error, APIStatusError):
            return error.status_code

        match = re.search(r"\b(429|500|502|503|504)\b", str(error))
        if match:
            return int(match.group(1))
        return None

    def _dump_parsed(self, parsed: Any) -> dict[str, Any]:
        if hasattr(parsed, "model_dump"):
            return parsed.model_dump()
        return dict(parsed)

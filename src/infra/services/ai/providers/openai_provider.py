"""OpenAI implementation of AIProviderPort using the native Responses API."""

from __future__ import annotations

import base64
import re
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from src.domain.ports.ai_provider_port import AICapability, AIProviderPort
from src.infra.services.ai.openai_prompt_cache_policy import OpenAIPromptCachePolicy


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
        self._client = AsyncOpenAI(
            api_key=api_key,
            timeout=request_timeout_seconds,
            max_retries=max_retries,
        )
        self._store_responses = store_responses
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
        prompt_cache_kwargs = self._prompt_cache_kwargs(
            model=model,
            purpose_hint=kwargs.get("purpose_hint"),
            system_message=system_message,
        )
        if schema is not None:
            response = await self._client.responses.parse(
                model=model,
                input=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                text_format=schema,
                max_output_tokens=max_tokens,
                reasoning={"effort": "none"},
                store=self._store_responses,
                **prompt_cache_kwargs,
            )
            return self._dump_parsed(response.output_parsed)

        response = await self._client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            max_output_tokens=max_tokens,
            reasoning={"effort": "none"},
            store=self._store_responses,
            **prompt_cache_kwargs,
        )
        return {"raw_content": response.output_text}

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
        image_b64 = base64.b64encode(image_data).decode("ascii")
        image_data_url = f"data:{image_mime_type};base64,{image_b64}"
        prompt_cache_kwargs = self._prompt_cache_kwargs(
            model=model,
            purpose_hint=kwargs.get("purpose_hint"),
            system_message=system_message,
        )

        response = await self._client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_message or ""},
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": image_data_url,
                            "detail": "high",
                        },
                    ],
                },
            ],
            text_format=schema,
            max_output_tokens=max_tokens,
            reasoning={"effort": "none"},
            store=self._store_responses,
            **prompt_cache_kwargs,
        )
        return self._dump_parsed(response.output_parsed)

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

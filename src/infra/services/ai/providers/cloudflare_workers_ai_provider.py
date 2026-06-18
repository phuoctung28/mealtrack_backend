"""Cloudflare Workers AI implementation of AIProviderPort using LangChain."""
import logging
from typing import Any

import httpx
from langchain_cloudflare.chat_models import ChatCloudflareWorkersAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from src.domain.ports.ai_provider_port import AICapability, AIProviderPort
from src.infra.adapters.ai_json_utils import extract_json as extract_ai_json

logger = logging.getLogger(__name__)


class CloudflareWorkersAIProvider(AIProviderPort):
    """
    Cloudflare Workers AI provider via LangChain's ChatCloudflareWorkersAI.

    Vision is not supported. generate_with_vision raises NotImplementedError.
    """

    def __init__(
        self,
        account_id: str,
        api_token: str,
        text_model: str,
        gateway_id: str = "",
        timeout_seconds: int = 30,
        json_mode_enabled: bool = True,
    ) -> None:
        self._text_model = text_model
        self._json_mode_enabled = json_mode_enabled

        kwargs: dict[str, Any] = {
            "model": text_model,
            "account_id": account_id,
            "api_token": api_token,
            "request_timeout": timeout_seconds,
        }
        if gateway_id:
            kwargs["ai_gateway"] = gateway_id

        self._llm = ChatCloudflareWorkersAI(**kwargs)

    @property
    def provider_name(self) -> str:
        return "cloudflare-workers-ai"

    @property
    def supported_capabilities(self) -> set[AICapability]:
        return {AICapability.TEXT_GENERATION, AICapability.STRUCTURED_OUTPUT}

    def get_available_models(self) -> list[str]:
        return [self._text_model] if self._text_model else []

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
        """Invoke Cloudflare Workers AI via LangChain and return normalized dict."""
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))

        llm: Any = self._llm
        if max_tokens is not None:
            llm = self._llm.bind(max_tokens=max_tokens)

        ai_msg = await llm.ainvoke(messages)
        raw = ai_msg.content
        # content can be list[dict] when the model returns reasoning/thinking blocks
        if isinstance(raw, list):
            text = " ".join(
                block["text"]
                for block in raw
                if isinstance(block, dict) and block.get("type") == "text"
            )
        else:
            text = raw

        if not text.strip():
            raise ValueError(
                f"[CF-WORKERS-AI] Model returned empty response for model={model}"
            )

        logger.debug(
            "[CF-WORKERS-AI-SUCCESS] model=%s response_type=%s",
            model,
            response_type,
        )

        if schema is not None:
            parsed_dict = extract_ai_json(text)
            try:
                instance = schema(**parsed_dict)
            except ValidationError as exc:
                raise ValueError(
                    f"[CF-WORKERS-AI] Schema validation failed: {exc}"
                ) from exc
            return instance.model_dump()

        if response_type == "json":
            return extract_ai_json(text)

        return {"raw_content": text}

    async def generate_with_vision(
        self,
        model: str,
        prompt: str,
        image_data: bytes,
        system_message: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Not supported in v1."""
        raise NotImplementedError(
            "CloudflareWorkersAIProvider does not support vision in v1. "
            "Use GeminiProvider for image-based tasks."
        )

    def extract_error_code(self, error: Exception) -> int | str | None:
        """Extract HTTP status code or 'timeout' from httpx exceptions bubbled through LangChain."""
        if isinstance(error, httpx.HTTPStatusError):
            return error.response.status_code
        if isinstance(error, httpx.TimeoutException):
            return "timeout"
        return None

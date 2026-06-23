"""Cloudflare Workers AI implementation of AIProviderPort using LangChain."""
import base64
import logging
from typing import Any

import httpx
from langchain_cloudflare.chat_models import ChatCloudflareWorkersAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from src.domain.ports.ai_provider_port import AICapability, AIProviderPort
from src.infra.adapters.ai_json_utils import extract_json as extract_ai_json
from src.infra.services.ai.ai_vision_errors import AIVisionError, AIVisionFailureKind

logger = logging.getLogger(__name__)

_CF_REST_BASE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"


class CloudflareWorkersAIProvider(AIProviderPort):
    """
    Cloudflare Workers AI provider via LangChain's ChatCloudflareWorkersAI.

    Text path: LangChain adapter.
    Vision path: direct Workers AI REST call with httpx (when vision_model configured).
    """

    def __init__(
        self,
        account_id: str,
        api_token: str,
        text_model: str,
        gateway_id: str = "",
        timeout_seconds: int = 30,
        json_mode_enabled: bool = True,
        vision_model: str = "",
        vision_enabled: bool = False,
    ) -> None:
        self._text_model = text_model
        self._json_mode_enabled = json_mode_enabled
        self._account_id = account_id
        self._api_token = api_token
        self._timeout_seconds = timeout_seconds
        self._vision_model = vision_model
        self._vision_enabled = vision_enabled and bool(vision_model)

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
        caps = {AICapability.TEXT_GENERATION, AICapability.STRUCTURED_OUTPUT}
        if self._vision_enabled:
            caps.add(AICapability.VISION)
        return caps

    def get_available_models(self) -> list[str]:
        models = [self._text_model] if self._text_model else []
        if self._vision_enabled and self._vision_model and self._vision_model != self._text_model:
            models.append(self._vision_model)
        return models

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

    def _build_vision_payload(
        self,
        prompt: str,
        image_data: bytes,
        system_message: str | None,
        max_tokens: int,
    ) -> dict[str, Any]:
        b64 = base64.b64encode(image_data).decode("ascii")
        user_content: list[dict] = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]
        messages: list[dict] = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": user_content})
        return {"messages": messages, "max_tokens": max_tokens, "temperature": 0.2}

    async def _post_workers_ai(self, model: str, payload: dict) -> dict:
        url = _CF_REST_BASE.format(account_id=self._account_id, model=model)
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    def _extract_response_text(self, raw: dict) -> str:
        result = raw.get("result", {})
        if isinstance(result, dict):
            if "response" in result:
                return str(result["response"])
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
        if isinstance(result, str):
            return result
        return ""

    async def generate_with_vision(
        self,
        model: str,
        prompt: str,
        image_data: bytes,
        system_message: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send image to Workers AI REST endpoint and return schema-validated dict."""
        from pydantic import ValidationError as PydanticValidationError
        from src.domain.parsers.vision_response_models import VisionAnalyzeResponse

        if not self._vision_enabled:
            raise NotImplementedError(
                "CloudflareWorkersAIProvider: vision not configured. "
                "Set CLOUDFLARE_WORKERS_AI_VISION_ENABLED=true and a vision model."
            )

        max_tokens: int = kwargs.get("max_tokens", 4096)
        payload = self._build_vision_payload(prompt, image_data, system_message, max_tokens)
        raw = await self._post_workers_ai(model, payload)
        text = self._extract_response_text(raw)

        if not text.strip():
            raise ValueError(
                f"[CF-WORKERS-AI-VISION] Model returned empty response for model={model}"
            )

        logger.debug("[CF-WORKERS-AI-VISION-SUCCESS] model=%s", model)

        try:
            parsed = extract_ai_json(text)
        except ValueError as exc:
            raise AIVisionError(
                f"[CF-WORKERS-AI-VISION-PARSE-FAIL] provider=cloudflare-workers-ai model={model}",
                kind=AIVisionFailureKind.json_parse,
                provider="cloudflare-workers-ai",
                model=model,
            ) from exc

        # Validate against schema — return normalized dict or raise classified error
        try:
            validated = VisionAnalyzeResponse.model_validate(parsed)
            return validated.model_dump()
        except PydanticValidationError as exc:
            raise AIVisionError(
                f"[CF-WORKERS-AI-VISION-SCHEMA-FAIL] provider=cloudflare-workers-ai model={model}",
                kind=AIVisionFailureKind.schema_validation,
                provider="cloudflare-workers-ai",
                model=model,
            ) from exc

    def extract_error_code(self, error: Exception) -> int | str | None:
        """Extract HTTP status code or 'timeout' from httpx exceptions bubbled through LangChain."""
        if isinstance(error, httpx.HTTPStatusError):
            return error.response.status_code
        if isinstance(error, httpx.TimeoutException):
            return "timeout"
        return None

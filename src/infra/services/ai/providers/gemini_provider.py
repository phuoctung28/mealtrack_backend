"""Gemini implementation of AIProviderPort."""
import asyncio
import logging
import re
from typing import Any

from google import genai
from google.genai.types import HttpOptions
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from src.domain.model.ai.nutrition_contracts import VisionNutritionResponse
from src.domain.ports.ai_provider_port import AICapability, AIProviderPort
from src.infra.adapters.ai_json_utils import (
    extract_json as extract_ai_json,
)
from src.infra.config.settings import get_settings
from src.infra.services.ai.ai_vision_errors import AIVisionError, AIVisionFailureKind
from src.infra.services.ai.gemini_model_config import GeminiModelPurpose
from src.infra.services.ai.gemini_model_manager import GeminiModelManager
from src.observability import increment_metric

logger = logging.getLogger(__name__)

MODEL_PURPOSE_MAP = {
    "gemini-3.5-flash": GeminiModelPurpose.GENERAL,
    "gemini-3.1-flash-lite": GeminiModelPurpose.GENERAL,
    "gemini-2.5-flash": GeminiModelPurpose.GENERAL,
    "gemini-2.5-flash-lite": GeminiModelPurpose.MEAL_NAMES,
}

_PURPOSE_HINT_MAP: dict[str, GeminiModelPurpose] = {
    "recipe":          GeminiModelPurpose.RECIPE,
    "barcode":         GeminiModelPurpose.BARCODE,
    "meal_names":      GeminiModelPurpose.MEAL_NAMES,
    "discovery":       GeminiModelPurpose.MEAL_NAMES,
    "parse_text":      GeminiModelPurpose.GENERAL,
    "ingredient_scan": GeminiModelPurpose.GENERAL,
    "meal_scan":       GeminiModelPurpose.GENERAL,
    "general":         GeminiModelPurpose.GENERAL,
}


class GeminiProvider(AIProviderPort):
    """Gemini implementation using existing GeminiModelManager."""

    AVAILABLE_MODELS = [
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]

    def __init__(self) -> None:
        self._model_manager = GeminiModelManager.get_instance()
        self._gateway_client: genai.Client | None = self._build_gateway_client()

    def _build_gateway_client(self) -> "genai.Client | None":
        settings = get_settings()
        if not settings.CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED:
            return None
        account_id: str = settings.CLOUDFLARE_ACCOUNT_ID or ""
        gateway_id: str = settings.CLOUDFLARE_AI_GATEWAY_ID or ""
        api_key: str = settings.GOOGLE_API_KEY or ""
        if not (account_id and gateway_id and api_key):
            logger.warning(
                "[GEMINI-GATEWAY] CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED=true "
                "but account_id/gateway_id/api_key missing — gateway client disabled"
            )
            return None
        base_url = (
            f"https://gateway.ai.cloudflare.com/v1"
            f"/{account_id}/{gateway_id}/google-ai-studio"
        )
        return genai.Client(
            api_key=api_key,
            http_options=HttpOptions(
                base_url=base_url,
                headers={
                    "cf-aig-skip-cache": "true",
                    "cf-aig-collect-log-payload": "false",
                },
            ),
        )

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def supported_capabilities(self) -> set[AICapability]:
        return {
            AICapability.TEXT_GENERATION,
            AICapability.VISION,
            AICapability.STRUCTURED_OUTPUT,
        }

    def get_available_models(self) -> list[str]:
        return self.AVAILABLE_MODELS.copy()

    async def generate(
        self,
        model: str,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: int | None = None,
        schema: type | None = None,
        purpose_hint: str | None = None,  # ModelPurpose.value string
        cache_name: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate text using Gemini."""
        if purpose_hint is not None:
            purpose = _PURPOSE_HINT_MAP.get(purpose_hint, GeminiModelPurpose.GENERAL)
        else:
            purpose = MODEL_PURPOSE_MAP.get(model, GeminiModelPurpose.GENERAL)

        response_mime_type = None
        if not schema and response_type == "json":
            response_mime_type = "application/json"

        extra_kwargs = {}
        if cache_name:
            extra_kwargs["cached_content"] = cache_name

        llm = self._model_manager.get_model_for_purpose(
            purpose=purpose,
            model_name=model,
            max_output_tokens=max_tokens,
            response_mime_type=response_mime_type,
            **extra_kwargs,
        )

        # When using explicit cache, system message is already in cache — omit it to avoid duplication errors
        messages = []
        if cache_name:
            # system content is already in the Gemini cache — omit to avoid 400 error
            pass
        elif system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))

        if schema:
            llm_structured = llm.with_structured_output(schema, include_raw=True)
            result = await asyncio.to_thread(llm_structured.invoke, messages)
            parsed = result.get("parsed") if isinstance(result, dict) else result
            if parsed is None:
                raise ValueError("Structured output returned None")
            if hasattr(parsed, "model_dump"):
                return parsed.model_dump()
            return dict(parsed)

        response = await asyncio.to_thread(llm.invoke, messages)
        content = response.content

        if response_type == "json":
            return self._extract_json(content)
        return {"raw_content": content}

    async def _generate_vision_via_gateway(
        self,
        model: str,
        prompt: str,
        image_data: bytes,
        system_message: str | None,
        max_tokens: int,
        purpose_hint: str,
    ) -> dict[str, Any]:
        """Call Gemini vision through CF AI Gateway using google-genai SDK."""
        from google.genai import types as genai_types

        config = genai_types.GenerateContentConfig(
            system_instruction=system_message or None,
            max_output_tokens=max_tokens,
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=VisionNutritionResponse,
        )
        parts: list[Any] = [
            genai_types.Part.from_text(text=prompt),
            genai_types.Part.from_bytes(data=image_data, mime_type="image/jpeg"),
        ]

        # Use async API directly — google-genai .aio namespace provides native async calls
        response = await self._gateway_client.aio.models.generate_content(  # type: ignore[union-attr]
            model=model,
            contents=[genai_types.Content(role="user", parts=parts)],
            config=config,
        )

        # Prefer response.parsed when response_schema is set — SDK populates it directly
        if response.parsed is not None:
            if hasattr(response.parsed, "model_dump"):
                return response.parsed.model_dump()
            return self._validate_vision_response(response.parsed, model)

        text = response.text
        if not text or not text.strip():
            raise ValueError(f"[GEMINI-GATEWAY-VISION] Empty response for model={model}")

        parsed = self._extract_json(text)
        return self._validate_vision_response(parsed, model)

    async def generate_with_vision(
        self,
        model: str,
        prompt: str,
        image_data: bytes,
        system_message: str | None = None,
        purpose_hint: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate with image input, using structured output first."""
        import base64

        max_tokens: int = kwargs.get("max_tokens", 4096)

        # Try CF AI Gateway path first when configured
        if self._gateway_client is not None:
            try:
                return await self._generate_vision_via_gateway(
                    model=model,
                    prompt=prompt,
                    image_data=image_data,
                    system_message=system_message,
                    max_tokens=max_tokens,
                    purpose_hint=purpose_hint or "",
                )
            except Exception as exc:
                logger.warning("[GEMINI-GATEWAY-VISION-FALLBACK] model=%s error=%s", model, exc)
                increment_metric(
                    "ai.vision.gateway.fallback.count",
                    attributes={"provider": "gemini", "model": model},
                )

        if purpose_hint is not None:
            purpose = _PURPOSE_HINT_MAP.get(purpose_hint, GeminiModelPurpose.GENERAL)
        else:
            purpose = MODEL_PURPOSE_MAP.get(model, GeminiModelPurpose.GENERAL)

        llm = self._model_manager.get_model_for_purpose(
            purpose=purpose,
            model_name=model,
            max_output_tokens=max_tokens,
        )

        image_b64 = base64.b64encode(image_data).decode("utf-8")
        image_url = f"data:image/jpeg;base64,{image_b64}"

        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]
            )
        )

        # Try structured output first
        try:
            structured_llm = llm.with_structured_output(
                VisionNutritionResponse.model_json_schema(),
                method="json_schema",
                include_raw=True,
            )
            result = await asyncio.to_thread(structured_llm.invoke, messages)
            parsed = result.get("parsed") if isinstance(result, dict) else result
            if parsed is not None:
                if hasattr(parsed, "model_dump"):
                    return parsed.model_dump()
                if isinstance(parsed, dict):
                    return self._validate_vision_response(parsed, model)
        except Exception:
            logger.debug("[GEMINI-VISION-STRUCTURED-FALLBACK] model=%s", model)

        # Fallback to raw text parse
        response = await asyncio.to_thread(llm.invoke, messages)
        try:
            parsed = self._extract_json(response.content)
            return self._validate_vision_response(parsed, model)
        except ValueError as exc:
            raise AIVisionError(
                f"[GEMINI-VISION-PARSE-FAIL] provider=gemini model={model}",
                kind=AIVisionFailureKind.json_parse,
                provider="gemini",
                model=model,
            ) from exc

    def extract_error_code(self, error: Exception) -> int | str | None:
        """Extract status code or error type from exception."""
        error_str = str(error)

        code_match = re.search(r"\b(503|429|500|502|504)\b", error_str)
        if code_match:
            return int(code_match.group(1))

        if "timeout" in error_str.lower():
            return "timeout"

        return None

    def _extract_json(self, content: str) -> dict[str, Any]:
        """Extract JSON from response content."""
        return extract_ai_json(content)

    def _validate_vision_response(self, data: Any, model: str) -> dict[str, Any]:
        try:
            return VisionNutritionResponse.model_validate(data).model_dump()
        except ValidationError as exc:
            raise AIVisionError(
                f"[GEMINI-VISION-SCHEMA-FAIL] provider=gemini model={model}",
                kind=AIVisionFailureKind.schema_validation,
                provider="gemini",
                model=model,
            ) from exc

"""Gemini implementation of AIProviderPort."""
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Union

from langchain_core.messages import HumanMessage, SystemMessage

from src.domain.ports.ai_provider_port import AICapability, AIProviderPort
from src.infra.services.ai.gemini_model_manager import GeminiModelManager
from src.infra.services.ai.gemini_model_config import GeminiModelPurpose

logger = logging.getLogger(__name__)

MODEL_PURPOSE_MAP = {
    "gemini-2.5-flash": GeminiModelPurpose.GENERAL,
    "gemini-2.5-flash-lite": GeminiModelPurpose.MEAL_NAMES,
}


class GeminiProvider(AIProviderPort):
    """Gemini implementation using existing GeminiModelManager."""

    AVAILABLE_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

    def __init__(self) -> None:
        self._model_manager = GeminiModelManager.get_instance()

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def supported_capabilities(self) -> Set[AICapability]:
        return {
            AICapability.TEXT_GENERATION,
            AICapability.VISION,
            AICapability.STRUCTURED_OUTPUT,
        }

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
        """Generate text using Gemini."""
        purpose = MODEL_PURPOSE_MAP.get(model, GeminiModelPurpose.GENERAL)

        response_mime_type = None
        if not schema and response_type == "json":
            response_mime_type = "application/json"

        llm = self._model_manager.get_model_for_purpose(
            purpose=purpose,
            max_output_tokens=max_tokens,
            response_mime_type=response_mime_type,
        )

        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=prompt),
        ]

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

    async def generate_with_vision(
        self,
        model: str,
        prompt: str,
        image_data: bytes,
        system_message: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate with image input."""
        import base64

        purpose = MODEL_PURPOSE_MAP.get(model, GeminiModelPurpose.GENERAL)
        llm = self._model_manager.get_model_for_purpose(
            purpose=purpose,
            max_output_tokens=kwargs.get("max_tokens", 2048),
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

        response = await asyncio.to_thread(llm.invoke, messages)
        return self._extract_json(response.content)

    def extract_error_code(self, error: Exception) -> Optional[Union[int, str]]:
        """Extract status code or error type from exception."""
        error_str = str(error)

        code_match = re.search(r"\b(503|429|500|502|504)\b", error_str)
        if code_match:
            return int(code_match.group(1))

        if "timeout" in error_str.lower():
            return "timeout"

        return None

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract JSON from response content."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not extract JSON from response: {content[:200]}")

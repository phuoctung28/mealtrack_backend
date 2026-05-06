"""Mistral AI provider implementation."""
import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Union

from src.domain.ports.ai_provider_port import AICapability, AIProviderPort

logger = logging.getLogger(__name__)


class MistralProvider(AIProviderPort):
    """
    Mistral AI provider implementation.

    Supports text generation and vision (via Pixtral model).
    Uses OpenAI-compatible API for simplicity.
    """

    # Model options - using latest aliases for auto-updates
    AVAILABLE_MODELS = [
        "mistral-small-latest",   # Fast, good for simple tasks
        "mistral-large-latest",   # Most capable
        "pixtral-12b-2409",       # Vision model
    ]

    def __init__(self) -> None:
        self._api_key = os.getenv("MISTRAL_API_KEY")
        if not self._api_key:
            logger.warning("MISTRAL_API_KEY not set - Mistral provider will not be available")

    @property
    def provider_name(self) -> str:
        return "mistral"

    @property
    def supported_capabilities(self) -> Set[AICapability]:
        return {
            AICapability.TEXT_GENERATION,
            AICapability.VISION,
            AICapability.STRUCTURED_OUTPUT,
        }

    def get_available_models(self) -> List[str]:
        return self.AVAILABLE_MODELS.copy()

    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        return self._api_key is not None

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
        """Generate text using Mistral API."""
        if not self._api_key:
            raise RuntimeError("MISTRAL_API_KEY not configured")

        from mistralai.client import Mistral

        client = Mistral(api_key=self._api_key)

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]

        # Build request parameters
        request_params = {
            "model": model,
            "messages": messages,
        }

        if max_tokens:
            request_params["max_tokens"] = max_tokens

        if response_type == "json":
            request_params["response_format"] = {"type": "json_object"}

        try:
            response = await asyncio.to_thread(
                client.chat.complete,
                **request_params,
            )

            content = response.choices[0].message.content

            if response_type == "json":
                return self._extract_json(content)
            return {"raw_content": content}

        except Exception as e:
            logger.error(f"[MISTRAL-ERROR] model={model} | error={str(e)[:200]}")
            raise

    async def generate_with_vision(
        self,
        model: str,
        prompt: str,
        image_data: bytes,
        system_message: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate with vision using Pixtral model."""
        if not self._api_key:
            raise RuntimeError("MISTRAL_API_KEY not configured")

        import base64
        from mistralai.client import Mistral

        client = Mistral(api_key=self._api_key)

        # Use Pixtral for vision tasks
        vision_model = "pixtral-12b-2409"

        # Encode image
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        image_url = f"data:image/jpeg;base64,{image_b64}"

        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": image_url},
            ],
        })

        try:
            response = await asyncio.to_thread(
                client.chat.complete,
                model=vision_model,
                messages=messages,
            )

            content = response.choices[0].message.content
            return self._extract_json(content)

        except Exception as e:
            logger.error(f"[MISTRAL-VISION-ERROR] model={vision_model} | error={str(e)[:200]}")
            raise

    def extract_error_code(self, error: Exception) -> Optional[Union[int, str]]:
        """Extract status code or error type from exception."""
        error_str = str(error)

        # Check for HTTP status codes
        code_match = re.search(r"\b(503|429|500|502|504)\b", error_str)
        if code_match:
            return int(code_match.group(1))

        if "timeout" in error_str.lower():
            return "timeout"

        if "rate" in error_str.lower() and "limit" in error_str.lower():
            return 429

        return None

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract JSON from response content."""
        # Try direct parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try bare JSON object
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not extract JSON from response: {content[:200]}")

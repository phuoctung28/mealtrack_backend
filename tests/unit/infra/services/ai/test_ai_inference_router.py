from unittest.mock import AsyncMock

import pytest

from src.domain.model.ai.model_purpose import ModelPurpose
from src.domain.ports.ai_provider_port import AICapability
from src.infra.services.ai.ai_inference_router import AIInferenceRouter
from src.infra.services.ai.model_route import ModelRoute


class FakeProvider:
    def __init__(self, provider_name, capabilities, result=None, error=None):
        self.provider_name = provider_name
        self.supported_capabilities = capabilities
        self.generate = AsyncMock(return_value=result, side_effect=error)
        self.generate_with_vision = AsyncMock(return_value=result, side_effect=error)

    def get_available_models(self):
        return []

    def extract_error_code(self, error):
        text = str(error).lower()
        if "429" in text:
            return 429
        if "timeout" in text:
            return "timeout"
        return None


@pytest.mark.asyncio
async def test_router_uses_openai_first_for_vision():
    openai = FakeProvider(
        "openai",
        {AICapability.VISION, AICapability.STRUCTURED_OUTPUT},
        result={"dish_name": "Bowl"},
    )
    cloudflare = FakeProvider(
        "cloudflare-workers-ai",
        {AICapability.VISION, AICapability.STRUCTURED_OUTPUT},
        result={"dish_name": "Fallback"},
    )
    router = AIInferenceRouter(
        providers={"openai": openai, "cloudflare-workers-ai": cloudflare},
        routes={
            ModelPurpose.MEAL_SCAN: [
                ModelRoute(provider="openai", model="gpt-5.4-mini-2026-03-17"),
                ModelRoute(
                    provider="cloudflare-workers-ai",
                    model="@cf/google/gemma-4-26b-a4b-it",
                ),
            ],
            ModelPurpose.GENERAL: [
                ModelRoute(provider="openai", model="gpt-5.4-mini-2026-03-17"),
            ],
        },
    )

    result = await router.generate_with_vision(
        purpose=ModelPurpose.MEAL_SCAN,
        prompt="prompt",
        image_data=b"image",
        system_message="system",
    )

    assert result == {"dish_name": "Bowl"}
    openai.generate_with_vision.assert_awaited_once()
    cloudflare.generate_with_vision.assert_not_called()


@pytest.mark.asyncio
async def test_router_falls_back_once_after_transient_failure():
    openai = FakeProvider(
        "openai",
        {AICapability.VISION, AICapability.STRUCTURED_OUTPUT},
        error=RuntimeError("429 rate limit"),
    )
    cloudflare = FakeProvider(
        "cloudflare-workers-ai",
        {AICapability.VISION, AICapability.STRUCTURED_OUTPUT},
        result={"dish_name": "Fallback"},
    )
    router = AIInferenceRouter(
        providers={"openai": openai, "cloudflare-workers-ai": cloudflare},
        routes={
            ModelPurpose.MEAL_SCAN: [
                ModelRoute(provider="openai", model="gpt-5.4-mini-2026-03-17"),
                ModelRoute(
                    provider="cloudflare-workers-ai",
                    model="@cf/google/gemma-4-26b-a4b-it",
                ),
            ],
            ModelPurpose.GENERAL: [
                ModelRoute(provider="openai", model="gpt-5.4-mini-2026-03-17"),
            ],
        },
    )

    result = await router.generate_with_vision(
        purpose=ModelPurpose.MEAL_SCAN,
        prompt="prompt",
        image_data=b"image",
        system_message="system",
    )

    assert result == {"dish_name": "Fallback"}
    openai.generate_with_vision.assert_awaited_once()
    cloudflare.generate_with_vision.assert_awaited_once()

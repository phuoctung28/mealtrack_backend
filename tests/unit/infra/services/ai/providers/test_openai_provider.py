from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.domain.model.ai.nutrition_contracts import VisionNutritionResponse
from src.domain.ports.ai_provider_port import AICapability
from src.infra.services.ai.providers.openai_provider import OpenAIProvider


def _provider(store_responses=False):
    return OpenAIProvider(
        api_key="test-key",
        request_timeout_seconds=20,
        max_retries=1,
        store_responses=store_responses,
        prompt_cache_enabled=True,
        prompt_cache_retention="in_memory",
        prompt_cache_key_prefix="mealtrack-test",
    )


def _parsed_vision_response():
    return VisionNutritionResponse.model_validate(
        {
            "is_food": True,
            "dish_name": "Chicken rice bowl",
            "emoji": "🍚",
            "foods": [
                {
                    "name": "grilled chicken",
                    "quantity_g": 150.0,
                    "macros": {
                        "protein_g": 35.0,
                        "carbs_g": 0.0,
                        "fat_g": 5.0,
                    },
                    "confidence": 0.92,
                }
            ],
            "confidence": 0.88,
        }
    )


def test_openai_provider_capabilities():
    provider = _provider()

    assert provider.provider_name == "openai"
    assert AICapability.TEXT_GENERATION in provider.supported_capabilities
    assert AICapability.VISION in provider.supported_capabilities
    assert AICapability.STRUCTURED_OUTPUT in provider.supported_capabilities


@pytest.mark.asyncio
async def test_generate_with_vision_uses_responses_parse_and_store_false():
    provider = _provider()
    parsed = _parsed_vision_response()
    provider._client.responses.parse = AsyncMock(
        return_value=SimpleNamespace(output_parsed=parsed)
    )

    result = await provider.generate_with_vision(
        model="gpt-5.4-mini-2026-03-17",
        prompt="Identify food.",
        image_data=b"image-bytes",
        system_message="Return canonical JSON.",
        schema=VisionNutritionResponse,
        image_mime_type="image/png",
        max_tokens=1500,
    )

    assert result["emoji"] == "🍚"
    call_kwargs = provider._client.responses.parse.await_args.kwargs
    assert call_kwargs["model"] == "gpt-5.4-mini-2026-03-17"
    assert call_kwargs["store"] is False
    assert call_kwargs["text_format"] is VisionNutritionResponse
    user_content = call_kwargs["input"][1]["content"]
    assert user_content[1]["image_url"].startswith("data:image/png;base64,")
    assert user_content[1]["detail"] == "high"


@pytest.mark.asyncio
async def test_generate_structured_text_includes_prompt_cache_kwargs():
    provider = _provider()
    parsed = _parsed_vision_response()
    provider._client.responses.parse = AsyncMock(
        return_value=SimpleNamespace(output_parsed=parsed)
    )

    await provider.generate(
        model="gpt-5.4-mini-2026-03-17",
        prompt="Chicken rice bowl",
        system_message="Return canonical JSON.",
        schema=VisionNutritionResponse,
        purpose_hint="parse_text",
    )

    call_kwargs = provider._client.responses.parse.await_args.kwargs
    assert call_kwargs["prompt_cache_key"].startswith("mealtrack-test:parse_text:")
    assert call_kwargs["prompt_cache_retention"] == "in_memory"


@pytest.mark.asyncio
async def test_generate_with_vision_includes_prompt_cache_kwargs():
    provider = _provider()
    parsed = _parsed_vision_response()
    provider._client.responses.parse = AsyncMock(
        return_value=SimpleNamespace(output_parsed=parsed)
    )

    await provider.generate_with_vision(
        model="gpt-5.4-mini-2026-03-17",
        prompt="Identify food.",
        image_data=b"image-bytes",
        system_message="Return canonical JSON.",
        schema=VisionNutritionResponse,
        purpose_hint="meal_scan",
    )

    call_kwargs = provider._client.responses.parse.await_args.kwargs
    assert call_kwargs["prompt_cache_key"].startswith("mealtrack-test:meal_scan:")
    assert call_kwargs["prompt_cache_retention"] == "in_memory"

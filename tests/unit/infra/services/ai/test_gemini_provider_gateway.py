"""Unit tests — GeminiProvider CF AI Gateway client construction."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.model.ai.nutrition_contracts import VisionNutritionResponse

# DO NOT use importlib.reload — it pollutes GeminiModelManager singleton state across tests.
# Pattern: mock both GeminiModelManager.get_instance and get_settings before
# instantiating GeminiProvider() directly inside the patch context.

_MODULE = "src.infra.services.ai.providers.gemini_provider"
_MANAGER = "src.infra.services.ai.gemini_model_manager.GeminiModelManager.get_instance"


def _enabled_settings():
    s = MagicMock()
    s.CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED = True
    s.CLOUDFLARE_ACCOUNT_ID = "acct"
    s.CLOUDFLARE_AI_GATEWAY_ID = "gw"
    s.GOOGLE_API_KEY = "gkey"
    return s


def test_gateway_client_built_when_setting_enabled():
    from src.infra.services.ai.providers.gemini_provider import GeminiProvider

    with patch(f"{_MODULE}.get_settings", return_value=_enabled_settings()):
        with patch(_MANAGER, return_value=MagicMock()):
            with patch(f"{_MODULE}.genai.Client") as mock_client:
                provider = GeminiProvider()
                assert provider._gateway_client is not None
                mock_client.assert_called_once()
                call_kwargs = mock_client.call_args.kwargs
                http_opts = call_kwargs.get("http_options")
                assert http_opts is not None
                expected_url = "https://gateway.ai.cloudflare.com/v1/acct/gw/google-ai-studio"
                assert http_opts.base_url == expected_url


def test_gateway_client_none_when_setting_disabled():
    from src.infra.services.ai.providers.gemini_provider import GeminiProvider

    s = MagicMock()
    s.CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED = False
    with patch(f"{_MODULE}.get_settings", return_value=s):
        with patch(_MANAGER, return_value=MagicMock()):
            provider = GeminiProvider()
            assert provider._gateway_client is None


def test_gateway_client_none_when_account_id_missing():
    from src.infra.services.ai.providers.gemini_provider import GeminiProvider

    s = MagicMock()
    s.CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED = True
    s.CLOUDFLARE_ACCOUNT_ID = ""
    s.CLOUDFLARE_AI_GATEWAY_ID = "gw"
    s.GOOGLE_API_KEY = "gkey"
    with patch(f"{_MODULE}.get_settings", return_value=s):
        with patch(_MANAGER, return_value=MagicMock()):
            provider = GeminiProvider()
            assert provider._gateway_client is None


def test_gateway_client_none_when_gateway_id_missing():
    from src.infra.services.ai.providers.gemini_provider import GeminiProvider

    s = MagicMock()
    s.CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED = True
    s.CLOUDFLARE_ACCOUNT_ID = "acct"
    s.CLOUDFLARE_AI_GATEWAY_ID = ""
    s.GOOGLE_API_KEY = "gkey"
    with patch(f"{_MODULE}.get_settings", return_value=s):
        with patch(_MANAGER, return_value=MagicMock()):
            provider = GeminiProvider()
            assert provider._gateway_client is None


def test_gateway_client_none_when_api_key_missing():
    from src.infra.services.ai.providers.gemini_provider import GeminiProvider

    s = MagicMock()
    s.CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED = True
    s.CLOUDFLARE_ACCOUNT_ID = "acct"
    s.CLOUDFLARE_AI_GATEWAY_ID = "gw"
    s.GOOGLE_API_KEY = ""
    with patch(f"{_MODULE}.get_settings", return_value=s):
        with patch(_MANAGER, return_value=MagicMock()):
            provider = GeminiProvider()
            assert provider._gateway_client is None


@pytest.mark.asyncio
async def test_gateway_vision_uses_canonical_response_schema():
    from src.infra.services.ai.providers.gemini_provider import GeminiProvider

    parsed = VisionNutritionResponse.model_validate(
        {
            "dish_name": "Rice bowl",
            "foods": [
                {
                    "name": "rice",
                    "quantity_g": 180,
                    "macros": {"protein_g": 4, "carbs_g": 50, "fat_g": 1},
                }
            ],
            "confidence": 0.9,
        }
    )
    response = MagicMock()
    response.parsed = parsed

    with patch(f"{_MODULE}.get_settings", return_value=_enabled_settings()):
        with patch(_MANAGER, return_value=MagicMock()):
            with patch(f"{_MODULE}.genai.Client"):
                provider = GeminiProvider()

    gateway_client = MagicMock()
    gateway_client.aio.models.generate_content = AsyncMock(return_value=response)
    provider._gateway_client = gateway_client

    result = await provider._generate_vision_via_gateway(
        model="gemini-2.5-flash",
        prompt="analyze",
        image_data=b"fake-image",
        system_message="system",
        max_tokens=1024,
        purpose_hint="meal_scan",
    )

    config = gateway_client.aio.models.generate_content.await_args.kwargs["config"]
    assert config.response_schema is VisionNutritionResponse
    assert result["foods"][0]["quantity_g"] == 180

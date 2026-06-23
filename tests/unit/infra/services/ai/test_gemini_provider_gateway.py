"""Unit tests — GeminiProvider CF AI Gateway client construction."""
import pytest
from unittest.mock import MagicMock, patch

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
                assert "gateway.ai.cloudflare.com" in str(http_opts)


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

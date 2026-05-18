"""Tests for MistralProvider."""
from unittest.mock import AsyncMock, patch

import pytest

from src.domain.ports.ai_provider_port import AICapability
from src.infra.services.ai.providers.mistral_provider import MistralProvider


@pytest.fixture
def provider_with_key():
    """Provider with API key configured."""
    with patch.dict("os.environ", {"MISTRAL_API_KEY": "test-key"}):
        return MistralProvider()


@pytest.fixture
def provider_without_key():
    """Provider without API key."""
    with patch.dict("os.environ", {}, clear=True):
        # Remove MISTRAL_API_KEY if it exists
        import os
        key = os.environ.pop("MISTRAL_API_KEY", None)
        provider = MistralProvider()
        if key:
            os.environ["MISTRAL_API_KEY"] = key
        return provider


class TestProviderInterface:
    def test_provider_name(self, provider_with_key):
        assert provider_with_key.provider_name == "mistral"

    def test_supported_capabilities(self, provider_with_key):
        caps = provider_with_key.supported_capabilities
        assert AICapability.TEXT_GENERATION in caps
        assert AICapability.VISION in caps
        assert AICapability.STRUCTURED_OUTPUT in caps

    def test_get_available_models(self, provider_with_key):
        models = provider_with_key.get_available_models()
        assert "mistral-small-latest" in models
        assert "mistral-large-latest" in models

    def test_is_available_with_key(self, provider_with_key):
        assert provider_with_key.is_available() is True

    def test_is_available_without_key(self, provider_without_key):
        assert provider_without_key.is_available() is False


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_dict(self, provider_with_key):
        with patch.object(
            provider_with_key,
            "_complete_chat",
            new=AsyncMock(return_value={
                "choices": [{"message": {"content": '{"meal": "test"}'}}],
            }),
        ):

            result = await provider_with_key.generate(
                model="mistral-small-latest",
                prompt="test prompt",
                system_message="test system",
            )

            assert isinstance(result, dict)
            assert result["meal"] == "test"

    @pytest.mark.asyncio
    async def test_generate_raises_without_key(self, provider_without_key):
        with pytest.raises(RuntimeError, match="MISTRAL_API_KEY not configured"):
            await provider_without_key.generate(
                model="mistral-small-latest",
                prompt="test",
                system_message="test",
            )

    @pytest.mark.asyncio
    async def test_generate_with_json_response_format(self, provider_with_key):
        with patch.object(
            provider_with_key,
            "_complete_chat",
            new=AsyncMock(return_value={
                "choices": [{"message": {"content": '{"result": "success"}'}}],
            }),
        ) as mock_complete:

            await provider_with_key.generate(
                model="mistral-small-latest",
                prompt="test",
                system_message="system",
                response_type="json",
            )

            payload = mock_complete.call_args[0][0]
            assert payload["response_format"] == {"type": "json_object"}


class TestVision:
    @pytest.mark.asyncio
    async def test_generate_with_vision_uses_mistral_large(self, provider_with_key):
        with patch.object(
            provider_with_key,
            "_complete_chat",
            new=AsyncMock(return_value={
                "choices": [{"message": {"content": '{"food": "pizza"}'}}],
            }),
        ) as mock_complete:

            result = await provider_with_key.generate_with_vision(
                model="any-model",
                prompt="what food is this?",
                image_data=b"fake_image_bytes",
            )

            payload = mock_complete.call_args[0][0]
            assert payload["model"] == "mistral-large-latest"
            assert result["food"] == "pizza"


class TestErrorExtraction:
    def test_extract_503(self, provider_with_key):
        code = provider_with_key.extract_error_code(Exception("503 Service Unavailable"))
        assert code == 503

    def test_extract_429(self, provider_with_key):
        code = provider_with_key.extract_error_code(Exception("429 Too Many Requests"))
        assert code == 429

    def test_extract_rate_limit(self, provider_with_key):
        code = provider_with_key.extract_error_code(Exception("Rate limit exceeded"))
        assert code == 429

    def test_extract_timeout(self, provider_with_key):
        code = provider_with_key.extract_error_code(Exception("Request timeout"))
        assert code == "timeout"

    def test_extract_unknown(self, provider_with_key):
        code = provider_with_key.extract_error_code(Exception("random error"))
        assert code is None


class TestJsonExtraction:
    def test_extract_direct_json(self, provider_with_key):
        result = provider_with_key._extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_extract_json_from_code_block(self, provider_with_key):
        content = '```json\n{"key": "value"}\n```'
        result = provider_with_key._extract_json(content)
        assert result == {"key": "value"}

    def test_extract_json_from_text(self, provider_with_key):
        content = 'Here is the result: {"key": "value"} end.'
        result = provider_with_key._extract_json(content)
        assert result == {"key": "value"}

    def test_raises_on_invalid_json(self, provider_with_key):
        with pytest.raises(ValueError, match="Could not extract JSON"):
            provider_with_key._extract_json("no json here")

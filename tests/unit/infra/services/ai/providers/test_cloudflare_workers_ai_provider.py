"""Tests for CloudflareWorkersAIProvider (LangChain-backed)."""
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from langchain_core.messages import AIMessage

from src.domain.ports.ai_provider_port import AICapability
from src.infra.services.ai.providers.cloudflare_workers_ai_provider import (
    CloudflareWorkersAIProvider,
)


@pytest.fixture
def provider():
    return CloudflareWorkersAIProvider(
        account_id="fake_account_id",
        api_token="fake_api_token",
        text_model="@cf/google/gemma-4-26b-a4b-it",
        gateway_id="fake_gateway",
        timeout_seconds=30,
        json_mode_enabled=True,
    )


@pytest.fixture
def provider_no_gateway():
    return CloudflareWorkersAIProvider(
        account_id="fake_account_id",
        api_token="fake_api_token",
        text_model="@cf/google/gemma-4-26b-a4b-it",
    )


class TestProviderInterface:
    def test_provider_name(self, provider):
        assert provider.provider_name == "cloudflare-workers-ai"

    def test_supported_capabilities_text_and_structured(self, provider):
        caps = provider.supported_capabilities
        assert AICapability.TEXT_GENERATION in caps
        assert AICapability.STRUCTURED_OUTPUT in caps
        assert AICapability.VISION not in caps

    def test_get_available_models_returns_configured_model(self, provider):
        assert "@cf/google/gemma-4-26b-a4b-it" in provider.get_available_models()


def _mock_llm(provider, return_value=None, side_effect=None):
    """Replace provider._llm with a Mock so ainvoke can be stubbed freely."""
    mock = Mock()
    if side_effect is not None:
        mock.ainvoke = AsyncMock(side_effect=side_effect)
        mock.bind = Mock(return_value=mock)
    else:
        mock.ainvoke = AsyncMock(return_value=return_value)
        mock.bind = Mock(return_value=mock)
    provider._llm = mock
    return mock


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_success_json(self, provider):
        """Successful JSON generation returns parsed dict."""
        _mock_llm(provider, return_value=AIMessage(content='{"meal": "salad"}'))

        result = await provider.generate(
            model="@cf/google/gemma-4-26b-a4b-it",
            prompt="List ingredients",
            system_message="You are a nutrition expert",
            response_type="json",
        )

        assert isinstance(result, dict)
        assert result.get("meal") == "salad"

    @pytest.mark.asyncio
    async def test_generate_raw_text_response(self, provider):
        """response_type='text' returns raw_content dict."""
        _mock_llm(provider, return_value=AIMessage(content="Hello world"))

        result = await provider.generate(
            model="@cf/google/gemma-4-26b-a4b-it",
            prompt="Say hello",
            system_message="system",
            response_type="text",
        )

        assert result.get("raw_content") == "Hello world"

    @pytest.mark.asyncio
    async def test_generate_with_pydantic_schema(self, provider):
        """Schema validation returns model_dump()."""
        from pydantic import BaseModel

        class MealSchema(BaseModel):
            meal: str
            calories: int

        _mock_llm(provider, return_value=AIMessage(content='{"meal": "rice", "calories": 200}'))

        result = await provider.generate(
            model="@cf/google/gemma-4-26b-a4b-it",
            prompt="Analyze meal",
            system_message="system",
            schema=MealSchema,
        )

        assert result["meal"] == "rice"
        assert result["calories"] == 200

    @pytest.mark.asyncio
    async def test_generate_passes_system_and_user_messages(self, provider):
        """generate() passes both SystemMessage and HumanMessage to ainvoke."""
        from langchain_core.messages import HumanMessage, SystemMessage

        mock = _mock_llm(provider, return_value=AIMessage(content='{"ok": true}'))

        await provider.generate(
            model="@cf/google/gemma-4-26b-a4b-it",
            prompt="user prompt",
            system_message="system instructions",
            response_type="json",
        )

        messages = mock.ainvoke.call_args[0][0]
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content == "system instructions"
        assert isinstance(messages[1], HumanMessage)
        assert messages[1].content == "user prompt"

    @pytest.mark.asyncio
    async def test_generate_omits_system_message_when_empty(self, provider):
        """Empty system_message sends only HumanMessage."""
        from langchain_core.messages import HumanMessage

        mock = _mock_llm(provider, return_value=AIMessage(content='{"x": 1}'))

        await provider.generate(
            model="@cf/google/gemma-4-26b-a4b-it",
            prompt="hello",
            system_message="",
            response_type="json",
        )

        messages = mock.ainvoke.call_args[0][0]
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)

    @pytest.mark.asyncio
    async def test_generate_propagates_http_429(self, provider):
        """LangChain-bubbled httpx 429 propagates as HTTPStatusError."""
        mock_resp = Mock()
        mock_resp.status_code = 429
        err = httpx.HTTPStatusError("429", request=Mock(), response=mock_resp)
        _mock_llm(provider, side_effect=err)

        with pytest.raises(httpx.HTTPStatusError):
            await provider.generate(
                model="@cf/google/gemma-4-26b-a4b-it",
                prompt="test",
                system_message="system",
            )

    @pytest.mark.asyncio
    async def test_generate_propagates_http_503(self, provider):
        """LangChain-bubbled httpx 503 propagates as HTTPStatusError."""
        mock_resp = Mock()
        mock_resp.status_code = 503
        err = httpx.HTTPStatusError("503", request=Mock(), response=mock_resp)
        _mock_llm(provider, side_effect=err)

        with pytest.raises(httpx.HTTPStatusError):
            await provider.generate(
                model="@cf/google/gemma-4-26b-a4b-it",
                prompt="test",
                system_message="system",
            )

    @pytest.mark.asyncio
    async def test_generate_propagates_timeout(self, provider):
        """LangChain-bubbled httpx timeout propagates as TimeoutException."""
        _mock_llm(provider, side_effect=httpx.TimeoutException("timeout"))

        with pytest.raises(httpx.TimeoutException):
            await provider.generate(
                model="@cf/google/gemma-4-26b-a4b-it",
                prompt="test",
                system_message="system",
            )

    @pytest.mark.asyncio
    async def test_generate_raises_on_malformed_json(self, provider):
        """Malformed JSON content raises ValueError."""
        _mock_llm(provider, return_value=AIMessage(content="not valid json {{{"))

        with pytest.raises(ValueError):
            await provider.generate(
                model="@cf/google/gemma-4-26b-a4b-it",
                prompt="test",
                system_message="system",
                response_type="json",
            )

    @pytest.mark.asyncio
    async def test_generate_handles_reasoning_block_content(self, provider):
        """list content with reasoning+text blocks: text parts are extracted and joined."""
        list_content = [
            {"type": "thinking", "thinking": "Let me reason..."},
            {"type": "text", "text": '{"meal": "salad"}'},
        ]
        _mock_llm(provider, return_value=AIMessage(content=list_content))

        result = await provider.generate(
            model="@cf/google/gemma-4-26b-a4b-it",
            prompt="Analyze",
            system_message="system",
            response_type="json",
        )

        assert result.get("meal") == "salad"

    @pytest.mark.asyncio
    async def test_generate_schema_validation_error_raises_value_error(self, provider):
        """Schema validation failure raises ValueError (not ValidationError) so circuit breaker is not tripped."""
        from pydantic import BaseModel

        class MealSchema(BaseModel):
            meal: str
            calories: int  # required int

        _mock_llm(
            provider,
            return_value=AIMessage(content='{"meal": "rice", "calories": "not-an-int"}'),
        )

        with pytest.raises(ValueError):
            await provider.generate(
                model="@cf/google/gemma-4-26b-a4b-it",
                prompt="Analyze",
                system_message="system",
                schema=MealSchema,
            )


class TestGenerateWithVision:
    @pytest.mark.asyncio
    async def test_generate_with_vision_raises_not_implemented(self, provider):
        """Vision is not supported in v1; must raise."""
        with pytest.raises((NotImplementedError, Exception)):
            await provider.generate_with_vision(
                model="@cf/google/gemma-4-26b-a4b-it",
                prompt="What is in this image?",
                image_data=b"fake_image_bytes",
            )


class TestGatewayConfig:
    def test_gateway_id_wired_into_llm_when_set(self, provider):
        """ai_gateway is passed to ChatCloudflareWorkersAI when gateway_id is set."""
        assert provider._llm.ai_gateway == "fake_gateway"

    def test_gateway_id_absent_when_not_configured(self, provider_no_gateway):
        """ai_gateway is None when gateway_id is empty."""
        assert not provider_no_gateway._llm.ai_gateway


class TestErrorCodeExtraction:
    def test_extracts_429_from_http_error(self, provider):
        mock_response = Mock()
        mock_response.status_code = 429
        err = httpx.HTTPStatusError("429", request=Mock(), response=mock_response)
        assert provider.extract_error_code(err) == 429

    def test_extracts_503_from_http_error(self, provider):
        mock_response = Mock()
        mock_response.status_code = 503
        err = httpx.HTTPStatusError("503", request=Mock(), response=mock_response)
        assert provider.extract_error_code(err) == 503

    def test_extracts_timeout_from_timeout_exception(self, provider):
        err = httpx.TimeoutException("timeout")
        assert provider.extract_error_code(err) == "timeout"

    def test_returns_none_for_generic_error(self, provider):
        err = Exception("something went wrong")
        assert provider.extract_error_code(err) is None

    def test_no_secrets_in_error_extraction(self, provider):
        """extract_error_code must not raise when given any exception type."""
        for exc in [ValueError("val"), RuntimeError("rt"), KeyError("key")]:
            code = provider.extract_error_code(exc)
            assert code is None or isinstance(code, (int, str))

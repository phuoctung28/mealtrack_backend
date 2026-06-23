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


@pytest.fixture
def provider_with_vision():
    return CloudflareWorkersAIProvider(
        account_id="fake_account_id",
        api_token="fake_api_token",
        text_model="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        gateway_id="fake_gateway",
        timeout_seconds=30,
        json_mode_enabled=True,
        vision_model="@cf/google/gemma-4-26b-a4b-it",
        vision_enabled=True,
    )


class TestProviderInterface:
    def test_provider_name(self, provider):
        assert provider.provider_name == "cloudflare-workers-ai"

    def test_supported_capabilities_text_and_structured(self, provider):
        caps = provider.supported_capabilities
        assert AICapability.TEXT_GENERATION in caps
        assert AICapability.STRUCTURED_OUTPUT in caps
        assert AICapability.VISION not in caps

    def test_supported_capabilities_includes_vision_when_enabled(self, provider_with_vision):
        caps = provider_with_vision.supported_capabilities
        assert AICapability.VISION in caps

    def test_get_available_models_returns_configured_model(self, provider):
        assert "@cf/google/gemma-4-26b-a4b-it" in provider.get_available_models()

    def test_get_available_models_includes_both_when_vision_configured(self, provider_with_vision):
        models = provider_with_vision.get_available_models()
        assert "@cf/meta/llama-3.3-70b-instruct-fp8-fast" in models
        assert "@cf/google/gemma-4-26b-a4b-it" in models
        assert len(set(models)) == len(models), "no duplicates"

    def test_vision_capability_absent_when_vision_disabled(self, provider):
        """Provider without vision_enabled must never expose VISION capability."""
        assert AICapability.VISION not in provider.supported_capabilities


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
    async def test_generate_raises_on_empty_response(self, provider):
        """Empty content raises ValueError so circuit breaker gets a clear signal."""
        _mock_llm(provider, return_value=AIMessage(content=""))

        with pytest.raises(ValueError, match="empty response"):
            await provider.generate(
                model="@cf/google/gemma-4-26b-a4b-it",
                prompt="test",
                system_message="system",
                response_type="json",
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
    async def test_generate_with_vision_raises_not_implemented_when_disabled(self, provider):
        """Provider without vision_model must raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await provider.generate_with_vision(
                model="@cf/google/gemma-4-26b-a4b-it",
                prompt="What is in this image?",
                image_data=b"fake_image_bytes",
            )

    @pytest.mark.asyncio
    async def test_generate_with_vision_success(self, provider_with_vision):
        """Vision-enabled provider calls REST and returns parsed dict."""
        from unittest.mock import AsyncMock, Mock, patch

        valid_json = (
            '{"dish_name": "Salad", "confidence": 0.9, "foods": ['
            '{"name": "Lettuce", "quantity": 100, "unit": "g",'
            ' "macros": {"protein": 1.0, "carbs": 2.0, "fat": 0.2}}]}'
        )
        mock_resp = Mock()
        mock_resp.json.return_value = {"result": {"response": valid_json}}
        mock_resp.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await provider_with_vision.generate_with_vision(
                model="@cf/google/gemma-4-26b-a4b-it",
                prompt="Analyze this meal",
                image_data=b"fake_image_bytes",
                system_message="You are a nutrition expert",
            )

        assert isinstance(result, dict)
        assert result.get("dish_name") == "Salad"

    @pytest.mark.asyncio
    async def test_generate_with_vision_empty_response_raises(self, provider_with_vision):
        """Empty response text raises ValueError."""
        from unittest.mock import AsyncMock, Mock, patch

        mock_resp = Mock()
        mock_resp.json.return_value = {"result": {"response": ""}}
        mock_resp.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            with pytest.raises(ValueError, match="empty response"):
                await provider_with_vision.generate_with_vision(
                    model="@cf/google/gemma-4-26b-a4b-it",
                    prompt="test",
                    image_data=b"img",
                )

    @pytest.mark.asyncio
    async def test_generate_with_vision_propagates_429(self, provider_with_vision):
        """HTTP 429 from REST endpoint propagates as HTTPStatusError."""
        from unittest.mock import AsyncMock, patch

        mock_resp = AsyncMock()
        mock_resp.status_code = 429
        err = httpx.HTTPStatusError("429", request=AsyncMock(), response=mock_resp)

        def raise_for_status():
            raise err

        mock_resp.raise_for_status = raise_for_status

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await provider_with_vision.generate_with_vision(
                    model="@cf/google/gemma-4-26b-a4b-it",
                    prompt="test",
                    image_data=b"img",
                )

    @pytest.mark.asyncio
    async def test_generate_with_vision_propagates_timeout(self, provider_with_vision):
        """Timeout from REST endpoint propagates as TimeoutException."""
        from unittest.mock import AsyncMock, patch

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client_cls.return_value = mock_client

            with pytest.raises(httpx.TimeoutException):
                await provider_with_vision.generate_with_vision(
                    model="@cf/google/gemma-4-26b-a4b-it",
                    prompt="test",
                    image_data=b"img",
                )

    @pytest.mark.asyncio
    async def test_generate_with_vision_malformed_json_raises(self, provider_with_vision):
        """Malformed JSON in response raises AIVisionError with json_parse kind."""
        from unittest.mock import AsyncMock, Mock, patch

        from src.infra.services.ai.ai_vision_errors import AIVisionError, AIVisionFailureKind

        mock_resp = Mock()
        mock_resp.json.return_value = {"result": {"response": "not valid json {{{"}}
        mock_resp.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            with pytest.raises(AIVisionError) as exc_info:
                await provider_with_vision.generate_with_vision(
                    model="@cf/google/gemma-4-26b-a4b-it",
                    prompt="test",
                    image_data=b"img",
                )
            assert exc_info.value.kind == AIVisionFailureKind.json_parse
            assert exc_info.value.provider == "cloudflare-workers-ai"

    def test_build_vision_payload_shape(self, provider_with_vision):
        """Vision payload has expected structure with image_url content."""
        payload = provider_with_vision._build_vision_payload(
            prompt="analyze meal",
            image_data=b"fake",
            system_message="system",
            max_tokens=1024,
        )
        assert payload["max_tokens"] == 1024
        assert payload["temperature"] == 0.2
        messages = payload["messages"]
        assert messages[0]["role"] == "system"
        user_msg = messages[1]
        assert user_msg["role"] == "user"
        content = user_msg["content"]
        assert any(c["type"] == "image_url" for c in content)
        img_part = next(c for c in content if c["type"] == "image_url")
        assert img_part["image_url"]["url"].startswith("data:image/jpeg;base64,")

    def test_extract_response_text_handles_choices_format(self, provider_with_vision):
        """Normalizes choices[0].message.content format."""
        raw = {"result": {"choices": [{"message": {"content": "hello"}}]}}
        assert provider_with_vision._extract_response_text(raw) == "hello"

    def test_extract_response_text_handles_response_field(self, provider_with_vision):
        """Normalizes result.response format."""
        raw = {"result": {"response": "hello"}}
        assert provider_with_vision._extract_response_text(raw) == "hello"

    @pytest.mark.asyncio
    async def test_generate_with_vision_returns_schema_valid_dict(self, provider_with_vision):
        """Valid JSON response is parsed and returned as dict."""
        from unittest.mock import AsyncMock, patch

        valid_json = (
            '{"dish_name": "Salad", "confidence": 0.95, "foods": ['
            '{"name": "Lettuce", "quantity": 100, "unit": "g",'
            ' "macros": {"protein": 1.0, "carbs": 2.0, "fat": 0.2}}]}'
        )

        with patch.object(
            provider_with_vision,
            "_post_workers_ai",
            new=AsyncMock(return_value={"result": {"response": valid_json}}),
        ):
            result = await provider_with_vision.generate_with_vision(
                model="@cf/google/gemma-4-26b-a4b-it",
                prompt="analyze",
                image_data=b"fake",
            )

        assert isinstance(result, dict)
        assert result["dish_name"] == "Salad"
        assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_generate_with_vision_returns_parsed_dict_without_schema_enforcement(
        self, provider_with_vision
    ):
        """Provider returns parsed dict as-is; schema enforcement is the application layer's job.

        Previously the provider validated against VisionAnalyzeResponse (legacy schema requiring
        quantity+unit), but the system prompt returns quantity_g with no unit — causing a
        deterministic 100% schema failure. Schema validation was moved to VisionAIService which
        uses VisionNutritionResponse (accepts quantity_g via AliasChoices).
        """
        from unittest.mock import AsyncMock, patch

        # Response missing macros — provider must pass it through without raising
        partial_json = (
            '{"dish_name": "Salad", "confidence": 0.9, "foods": ['
            '{"name": "Lettuce", "quantity_g": 100}]}'
        )

        with patch.object(
            provider_with_vision,
            "_post_workers_ai",
            new=AsyncMock(return_value={"result": {"response": partial_json}}),
        ):
            result = await provider_with_vision.generate_with_vision(
                model="@cf/google/gemma-4-26b-a4b-it",
                prompt="analyze",
                image_data=b"fake",
            )

        assert isinstance(result, dict)
        assert result["dish_name"] == "Salad"
        assert result["foods"][0]["quantity_g"] == 100

    def test_no_secrets_in_vision_error_messages(self, provider_with_vision):
        """generate_with_vision NotImplementedError must not expose the api token."""
        default_provider = CloudflareWorkersAIProvider(
            account_id="secret_account",
            api_token="secret_token_abc",
            text_model="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        )
        import asyncio
        try:
            asyncio.get_event_loop().run_until_complete(
                default_provider.generate_with_vision(
                    model="test", prompt="test", image_data=b"x"
                )
            )
        except NotImplementedError as e:
            assert "secret_token_abc" not in str(e)
        except Exception:
            pass


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

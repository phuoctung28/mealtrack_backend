import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.domain.ports.ai_provider_port import AICapability
from src.infra.services.ai.providers.gemini_provider import GeminiProvider


@pytest.fixture
def mock_model_manager():
    manager = Mock()
    manager.model_name = "gemini-2.5-flash"
    manager.get_model_for_purpose = Mock(return_value=Mock())
    return manager


@pytest.fixture
def provider(mock_model_manager):
    with patch(
        "src.infra.services.ai.providers.gemini_provider.GeminiModelManager"
    ) as mock_cls:
        mock_cls.get_instance.return_value = mock_model_manager
        return GeminiProvider()


class TestProviderInterface:
    def test_provider_name(self, provider):
        assert provider.provider_name == "gemini"

    def test_supported_capabilities(self, provider):
        caps = provider.supported_capabilities
        assert AICapability.TEXT_GENERATION in caps
        assert AICapability.VISION in caps
        assert AICapability.STRUCTURED_OUTPUT in caps

    def test_get_available_models(self, provider):
        models = provider.get_available_models()
        assert "gemini-2.5-flash" in models
        assert "gemini-2.5-flash-lite" in models


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_dict(self, provider, mock_model_manager):
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = '{"meal": "test"}'
        mock_llm.invoke = Mock(return_value=mock_response)
        mock_model_manager.get_model_for_purpose.return_value = mock_llm

        result = await provider.generate(
            model="gemini-2.5-flash",
            prompt="test prompt",
            system_message="test system",
        )

        assert isinstance(result, dict)
        assert result["meal"] == "test"

    @pytest.mark.asyncio
    async def test_generate_raises_on_api_error(self, provider, mock_model_manager):
        mock_llm = Mock()
        mock_llm.invoke = Mock(side_effect=Exception("503 UNAVAILABLE"))
        mock_model_manager.get_model_for_purpose.return_value = mock_llm

        with pytest.raises(Exception, match="503"):
            await provider.generate(
                model="gemini-2.5-flash",
                prompt="test",
                system_message="test",
            )


class TestErrorExtraction:
    def test_extract_status_code_from_503(self, provider):
        code = provider.extract_error_code(Exception("503 UNAVAILABLE"))
        assert code == 503

    def test_extract_status_code_from_429(self, provider):
        code = provider.extract_error_code(Exception("429 RESOURCE_EXHAUSTED"))
        assert code == 429

    def test_extract_timeout(self, provider):
        code = provider.extract_error_code(Exception("Request timeout"))
        assert code == "timeout"

    def test_extract_unknown(self, provider):
        code = provider.extract_error_code(Exception("random error"))
        assert code is None


def test_purpose_temperatures_defined():
    from src.infra.services.ai.gemini_model_config import (
        GeminiModelPurpose,
        PURPOSE_TEMPERATURES,
    )
    assert PURPOSE_TEMPERATURES[GeminiModelPurpose.BARCODE] == 0.1
    assert PURPOSE_TEMPERATURES[GeminiModelPurpose.MEAL_NAMES] == 0.7
    assert PURPOSE_TEMPERATURES[GeminiModelPurpose.RECIPE] == 0.4
    assert PURPOSE_TEMPERATURES[GeminiModelPurpose.GENERAL] == 0.2


@pytest.mark.asyncio
async def test_recipe_purpose_hint_resolves_to_recipe_purpose(mock_model_manager):
    """purpose_hint='recipe' must resolve to GeminiModelPurpose.RECIPE,
    which triggers thinking_budget=0 in get_model_for_purpose."""
    from src.infra.services.ai.gemini_model_config import GeminiModelPurpose

    with patch(
        "src.infra.services.ai.providers.gemini_provider.GeminiModelManager"
    ) as mock_cls:
        mock_cls.get_instance.return_value = mock_model_manager
        p = GeminiProvider()

    mock_llm = Mock()
    mock_llm.invoke = Mock(return_value=Mock(content='{"emoji": "🍚"}'))
    mock_model_manager.get_model_for_purpose.return_value = mock_llm

    await p.generate(
        model="gemini-2.5-flash",
        prompt="test",
        system_message="system",
        purpose_hint="recipe",
    )

    call_kwargs = mock_model_manager.get_model_for_purpose.call_args[1]
    assert call_kwargs["purpose"] == GeminiModelPurpose.RECIPE


@pytest.mark.asyncio
async def test_no_purpose_hint_falls_back_to_model_map(mock_model_manager):
    """Without purpose_hint, MODEL_PURPOSE_MAP is used (backward compat)."""
    from src.infra.services.ai.gemini_model_config import GeminiModelPurpose

    with patch(
        "src.infra.services.ai.providers.gemini_provider.GeminiModelManager"
    ) as mock_cls:
        mock_cls.get_instance.return_value = mock_model_manager
        p = GeminiProvider()

    mock_llm = Mock()
    mock_llm.invoke = Mock(return_value=Mock(content='{"result": "ok"}'))
    mock_model_manager.get_model_for_purpose.return_value = mock_llm

    await p.generate(
        model="gemini-2.5-flash",
        prompt="test",
        system_message="system",
        # no purpose_hint
    )

    call_kwargs = mock_model_manager.get_model_for_purpose.call_args[1]
    assert call_kwargs["purpose"] == GeminiModelPurpose.GENERAL


@pytest.mark.asyncio
async def test_generate_passes_cached_content_when_available():
    """When cache_name is provided, get_model_for_purpose receives cached_content kwarg and system message is omitted."""
    from unittest.mock import MagicMock

    provider = GeminiProvider.__new__(GeminiProvider)
    mock_manager = MagicMock()
    mock_model = MagicMock()
    captured_messages = []

    def capture_invoke(msgs):
        captured_messages.extend(msgs)
        return MagicMock(content='{"emoji":"🍚"}')

    mock_model.invoke = capture_invoke
    mock_manager.get_model_for_purpose = MagicMock(return_value=mock_model)
    provider._model_manager = mock_manager

    with patch.object(provider, "_extract_json", return_value={"emoji": "🍚"}):
        await provider.generate(
            model="gemini-2.5-flash-lite",
            prompt="Recipe for chicken salad",
            system_message="You are a professional chef",
            purpose_hint="recipe",
            cache_name="cachedContents/abc123",
        )

    call_kwargs = mock_manager.get_model_for_purpose.call_args[1]
    assert call_kwargs.get("cached_content") == "cachedContents/abc123"

    from langchain_core.messages import SystemMessage
    assert not any(isinstance(m, SystemMessage) for m in captured_messages)


@pytest.mark.asyncio
async def test_generate_omits_system_message_when_cache_active():
    """When cache_name is set, SystemMessage is NOT added to messages."""
    from unittest.mock import MagicMock

    provider = GeminiProvider.__new__(GeminiProvider)
    mock_manager = MagicMock()
    mock_model = MagicMock()
    captured_messages = []

    def capture_invoke(msgs):
        captured_messages.extend(msgs)
        return MagicMock(content='{"result": "ok"}')

    mock_model.invoke = capture_invoke
    mock_manager.get_model_for_purpose = MagicMock(return_value=mock_model)
    provider._model_manager = mock_manager

    with patch.object(provider, "_extract_json", return_value={"result": "ok"}):
        await provider.generate(
            model="gemini-2.5-flash",
            prompt="test prompt",
            system_message="This is the system message",
            cache_name="cachedContents/xyz789",
        )

    from langchain_core.messages import SystemMessage
    assert not any(isinstance(m, SystemMessage) for m in captured_messages)

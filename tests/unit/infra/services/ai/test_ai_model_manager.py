from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import BaseModel

from src.domain.exceptions.ai_exceptions import AIUnavailableError
from src.infra.services.ai.ai_model_manager import AIModelManager, ModelPurpose
from src.infra.services.ai.provider_circuit_breaker import CircuitState


@pytest.fixture
def mock_gemini_provider():
    from src.domain.ports.ai_provider_port import AICapability

    provider = Mock()
    provider.provider_name = "gemini"
    provider.get_available_models.return_value = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]
    provider.supported_capabilities = {
        AICapability.TEXT_GENERATION,
        AICapability.VISION,
        AICapability.STRUCTURED_OUTPUT,
    }
    provider.generate = AsyncMock(return_value={"result": "success"})
    provider.generate_with_vision = AsyncMock(return_value={"result": "vision_success"})
    provider.extract_error_code = Mock(return_value=503)
    return provider


@pytest.fixture
def mock_circuit_breaker():
    breaker = Mock()
    breaker.get_state = Mock(return_value=CircuitState.CLOSED)
    breaker.filter_available = Mock(side_effect=lambda models: models)
    breaker.record_failure = Mock()
    breaker.record_success = Mock()
    breaker.should_trip = Mock(return_value=True)
    return breaker


@pytest.fixture
def manager(mock_gemini_provider, mock_circuit_breaker):
    with (
        patch(
            "src.infra.services.ai.ai_model_manager.GeminiProvider",
            return_value=mock_gemini_provider,
        ),
        patch(
            "src.infra.services.ai.ai_model_manager.ProviderCircuitBreaker",
            return_value=mock_circuit_breaker,
        ),
    ):
        return AIModelManager()


class TestModelSelection:
    def test_get_fallback_chain_for_meal_scan(self, manager):
        """Vision tasks use Gemini Flash-Lite first, Flash as fallback."""
        chain = manager.get_fallback_chain(ModelPurpose.MEAL_SCAN)
        assert chain == ["gemini-2.5-flash-lite", "gemini-2.5-flash"]

    def test_get_fallback_chain_for_ingredient_scan(self, manager):
        """Ingredient scan uses Gemini Flash-Lite first, Flash as fallback."""
        chain = manager.get_fallback_chain(ModelPurpose.INGREDIENT_SCAN)
        assert chain == ["gemini-2.5-flash-lite", "gemini-2.5-flash"]

    def test_get_fallback_chain_for_barcode(self, manager):
        """Barcode uses Flash-Lite (cheaper) first, Flash as fallback."""
        chain = manager.get_fallback_chain(ModelPurpose.BARCODE)
        assert chain == ["gemini-2.5-flash-lite", "gemini-2.5-flash"]

    def test_get_fallback_chain_for_parse_text(self, manager):
        """Parse text uses Gemini Lite first for short structured tasks."""
        chain = manager.get_fallback_chain(ModelPurpose.PARSE_TEXT)
        assert chain == ["gemini-2.5-flash-lite", "gemini-2.5-flash"]

    def test_recipe_purpose_exists(self, manager):
        """RECIPE is a valid purpose; RECIPE_PRIMARY and RECIPE_SECONDARY do not exist."""
        from src.infra.services.ai.ai_model_manager import ModelPurpose

        assert hasattr(ModelPurpose, "RECIPE")
        assert not hasattr(ModelPurpose, "RECIPE_PRIMARY")
        assert not hasattr(ModelPurpose, "RECIPE_SECONDARY")

    def test_recipe_chain_uses_flash_lite_first(self, manager):
        """Recipes use Gemini Flash-Lite first, Flash as fallback."""
        chain = manager.get_fallback_chain(ModelPurpose.RECIPE)
        assert chain == ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
        assert "mistral" not in " ".join(chain)

    def test_gemini_lite_prioritized_for_all_purposes(self, manager):
        """All model purposes use Gemini Flash-Lite first, Flash as fallback."""
        for purpose in (
            ModelPurpose.MEAL_SCAN,
            ModelPurpose.INGREDIENT_SCAN,
            ModelPurpose.BARCODE,
            ModelPurpose.PARSE_TEXT,
            ModelPurpose.MEAL_NAMES,
            ModelPurpose.DISCOVERY,
            ModelPurpose.RECIPE,
            ModelPurpose.GENERAL,
        ):
            assert manager.get_fallback_chain(purpose) == [
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash",
            ]

    def test_no_mistral_in_any_fallback_chain(self, manager):
        """No fallback chain should reference Mistral after removal."""
        from src.infra.services.ai.ai_model_manager import FALLBACK_CHAINS

        all_models = [m for chain in FALLBACK_CHAINS.values() for m in chain]
        assert not any("mistral" in m for m in all_models)

    def test_no_kimi_in_any_fallback_chain(self, manager):
        from src.infra.services.ai.ai_model_manager import FALLBACK_CHAINS

        all_models = [m for chain in FALLBACK_CHAINS.values() for m in chain]
        assert not any("kimi" in m for m in all_models)

    def test_no_deepseek_in_any_fallback_chain(self, manager):
        from src.infra.services.ai.ai_model_manager import FALLBACK_CHAINS

        all_models = [m for chain in FALLBACK_CHAINS.values() for m in chain]
        assert not any("deepseek" in m for m in all_models)

    def test_mistral_provider_not_imported(self, manager):
        """AIModelManager must not import or reference MistralProvider."""
        import inspect

        import src.infra.services.ai.ai_model_manager as module

        source = inspect.getsource(module)
        assert "MistralProvider" not in source
        assert "mistral_provider" not in source
        assert "DeepSeekProvider" not in source
        assert "deepseek_provider" not in source


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_success_on_primary(self, manager, mock_gemini_provider):
        result = await manager.generate(
            purpose=ModelPurpose.MEAL_SCAN,
            prompt="test",
            system_message="system",
        )
        assert result == {"result": "success"}
        mock_gemini_provider.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_fallback_on_primary_failure(
        self, manager, mock_gemini_provider, mock_circuit_breaker
    ):
        mock_gemini_provider.generate = AsyncMock(
            side_effect=[Exception("503 UNAVAILABLE"), {"result": "fallback"}]
        )

        result = await manager.generate(
            purpose=ModelPurpose.MEAL_SCAN,
            prompt="test",
            system_message="system",
        )

        assert result == {"result": "fallback"}
        assert mock_gemini_provider.generate.call_count == 2
        mock_circuit_breaker.record_failure.assert_called_once()
        mock_circuit_breaker.record_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_omits_cache_when_fallback_model_does_not_match(
        self, manager, mock_gemini_provider
    ):
        mock_gemini_provider.generate = AsyncMock(
            side_effect=[Exception("cache/model mismatch"), {"result": "fallback"}]
        )
        cache_manager = Mock()
        cache_manager.get_cache_name_for_model = AsyncMock(
            side_effect=["cachedContents/primary", None]
        )
        manager.set_cache_manager(cache_manager)

        result = await manager.generate(
            purpose=ModelPurpose.PARSE_TEXT,
            prompt="test",
            system_message="system",
        )

        assert result == {"result": "fallback"}
        assert mock_gemini_provider.generate.call_args_list[0].kwargs["cache_name"] == (
            "cachedContents/primary"
        )
        assert (
            mock_gemini_provider.generate.call_args_list[1].kwargs["cache_name"] is None
        )
        cache_manager.get_cache_name_for_model.assert_any_await(
            "text_parse", "gemini-2.5-flash-lite"
        )
        cache_manager.get_cache_name_for_model.assert_any_await(
            "text_parse", "gemini-2.5-flash"
        )

    @pytest.mark.asyncio
    async def test_generate_raises_when_all_fail(
        self, manager, mock_gemini_provider, mock_circuit_breaker
    ):
        mock_gemini_provider.generate = AsyncMock(
            side_effect=Exception("503 UNAVAILABLE")
        )

        with pytest.raises(AIUnavailableError) as exc_info:
            await manager.generate(
                purpose=ModelPurpose.MEAL_SCAN,
                prompt="test",
                system_message="system",
            )

        assert "gemini-2.5-flash" in exc_info.value.attempted_models

    @pytest.mark.asyncio
    async def test_generate_skips_open_circuits(
        self, manager, mock_gemini_provider, mock_circuit_breaker
    ):
        mock_circuit_breaker.filter_available = Mock(
            return_value=["gemini-2.5-flash-lite"]
        )

        await manager.generate(
            purpose=ModelPurpose.MEAL_SCAN,
            prompt="test",
            system_message="system",
        )

        call_args = mock_gemini_provider.generate.call_args
        assert call_args[1]["model"] == "gemini-2.5-flash-lite"

    @pytest.mark.asyncio
    async def test_generate_uses_gemini_lite_first_for_parse_text(
        self, manager, mock_gemini_provider
    ):
        mock_gemini_provider.generate = AsyncMock(return_value={"result": "gemini"})

        result = await manager.generate(
            purpose=ModelPurpose.PARSE_TEXT,
            prompt="test",
            system_message="system",
        )

        assert result == {"result": "gemini"}
        mock_gemini_provider.generate.assert_awaited_once()


class TestVision:
    @pytest.mark.asyncio
    async def test_generate_with_vision(self, manager, mock_gemini_provider):
        result = await manager.generate_with_vision(
            purpose=ModelPurpose.MEAL_SCAN,
            prompt="analyze",
            image_data=b"fake_image",
        )
        assert result == {"result": "vision_success"}

    @pytest.mark.asyncio
    async def test_generate_with_vision_forwards_schema(
        self, manager, mock_gemini_provider
    ):
        class DummyVisionResponse(BaseModel):
            result: str

        await manager.generate_with_vision(
            purpose=ModelPurpose.MEAL_SCAN,
            prompt="analyze",
            image_data=b"fake_image",
            system_message="system",
            schema=DummyVisionResponse,
        )

        call_kwargs = mock_gemini_provider.generate_with_vision.call_args.kwargs
        assert call_kwargs["schema"] is DummyVisionResponse
        assert call_kwargs["purpose_hint"] == "meal_scan"

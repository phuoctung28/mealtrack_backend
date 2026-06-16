"""Tests for GeminiService (formerly AIModelManager) — fallback chains, generate, vision."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import BaseModel

from src.domain.exceptions.ai_exceptions import AIUnavailableError
from src.infra.ai.gemini_service import GeminiService
from src.infra.ai.model_config import FALLBACK_CHAINS, ModelPurpose
from src.infra.ai.circuit_breaker import CircuitState


@pytest.fixture(autouse=True)
def reset_gemini_service():
    """Ensure singleton is clean for each test."""
    GeminiService.reset_instance()
    yield
    GeminiService.reset_instance()


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
def service(mock_circuit_breaker):
    """GeminiService with mocked circuit breaker and model pool bypassed."""
    with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):
        svc = GeminiService()
        svc._circuit_breaker = mock_circuit_breaker
        return svc


class TestModelSelection:
    def test_get_fallback_chain_for_meal_scan(self, service):
        """Vision tasks use Gemini Flash-Lite first, Flash as fallback."""
        chain = service.get_fallback_chain(ModelPurpose.MEAL_SCAN)
        assert chain == ["gemini-2.5-flash-lite", "gemini-2.5-flash"]

    def test_get_fallback_chain_for_ingredient_scan(self, service):
        chain = service.get_fallback_chain(ModelPurpose.INGREDIENT_SCAN)
        assert chain == ["gemini-2.5-flash-lite", "gemini-2.5-flash"]

    def test_get_fallback_chain_for_barcode(self, service):
        chain = service.get_fallback_chain(ModelPurpose.BARCODE)
        assert chain == ["gemini-2.5-flash-lite", "gemini-2.5-flash"]

    def test_get_fallback_chain_for_parse_text(self, service):
        chain = service.get_fallback_chain(ModelPurpose.PARSE_TEXT)
        assert chain == ["gemini-2.5-flash-lite", "gemini-2.5-flash"]

    def test_recipe_purpose_exists(self, service):
        assert hasattr(ModelPurpose, "RECIPE")
        assert not hasattr(ModelPurpose, "RECIPE_PRIMARY")
        assert not hasattr(ModelPurpose, "RECIPE_SECONDARY")

    def test_recipe_chain_uses_flash_lite_first(self, service):
        chain = service.get_fallback_chain(ModelPurpose.RECIPE)
        assert chain == ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
        assert "mistral" not in " ".join(chain)

    def test_gemini_lite_prioritized_for_all_purposes(self, service):
        for purpose in ModelPurpose:
            assert service.get_fallback_chain(purpose) == [
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash",
            ]

    def test_no_mistral_in_any_fallback_chain(self, service):
        all_models = [m for chain in FALLBACK_CHAINS.values() for m in chain]
        assert not any("mistral" in m for m in all_models)

    def test_no_kimi_in_any_fallback_chain(self, service):
        all_models = [m for chain in FALLBACK_CHAINS.values() for m in chain]
        assert not any("kimi" in m for m in all_models)

    def test_no_deepseek_in_any_fallback_chain(self, service):
        all_models = [m for chain in FALLBACK_CHAINS.values() for m in chain]
        assert not any("deepseek" in m for m in all_models)

    def test_gemini_service_does_not_import_mistral(self):
        import inspect
        import src.infra.ai.gemini_service as module

        source = inspect.getsource(module)
        assert "MistralProvider" not in source
        assert "mistral_provider" not in source
        assert "DeepSeekProvider" not in source
        assert "deepseek_provider" not in source


class TestTextJson:
    @pytest.mark.asyncio
    async def test_text_json_success_on_primary(self, service):
        service._call_text = AsyncMock(return_value={"result": "success"})
        service._resolve_cache_name = AsyncMock(return_value=None)

        result = await service.text_json(
            purpose=ModelPurpose.MEAL_SCAN,
            user_prompt="test",
            system_prompt="system",
        )
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_text_json_fallback_on_primary_failure(
        self, service, mock_circuit_breaker
    ):
        service._resolve_cache_name = AsyncMock(return_value=None)
        service._call_text = AsyncMock(
            side_effect=[Exception("503 UNAVAILABLE"), {"result": "fallback"}]
        )

        result = await service.text_json(
            purpose=ModelPurpose.MEAL_SCAN,
            user_prompt="test",
            system_prompt="system",
        )

        assert result == {"result": "fallback"}
        assert service._call_text.call_count == 2
        mock_circuit_breaker.record_failure.assert_called_once()
        mock_circuit_breaker.record_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_text_json_omits_cache_when_fallback_model_does_not_match(
        self, service
    ):
        service._call_text = AsyncMock(
            side_effect=[Exception("cache/model mismatch"), {"result": "fallback"}]
        )
        cache_manager = Mock()
        cache_manager.get_cache_name_for_model = AsyncMock(
            side_effect=["cachedContents/primary", None]
        )
        service.set_cache_manager(cache_manager)

        result = await service.text_json(
            purpose=ModelPurpose.PARSE_TEXT,
            user_prompt="test",
            system_prompt="system",
        )

        assert result == {"result": "fallback"}
        first_call_kwargs = service._call_text.call_args_list[0].kwargs
        second_call_kwargs = service._call_text.call_args_list[1].kwargs
        assert first_call_kwargs["cache_name"] == "cachedContents/primary"
        assert second_call_kwargs["cache_name"] is None

    @pytest.mark.asyncio
    async def test_text_json_raises_when_all_fail(
        self, service, mock_circuit_breaker
    ):
        service._resolve_cache_name = AsyncMock(return_value=None)
        service._call_text = AsyncMock(side_effect=Exception("503 UNAVAILABLE"))

        with pytest.raises(AIUnavailableError) as exc_info:
            await service.text_json(
                purpose=ModelPurpose.MEAL_SCAN,
                user_prompt="test",
                system_prompt="system",
            )

        assert "gemini-2.5-flash" in exc_info.value.attempted_models

    @pytest.mark.asyncio
    async def test_text_json_skips_open_circuits(self, service, mock_circuit_breaker):
        mock_circuit_breaker.filter_available = Mock(
            return_value=["gemini-2.5-flash-lite"]
        )
        service._resolve_cache_name = AsyncMock(return_value=None)
        service._call_text = AsyncMock(return_value={"result": "gemini"})

        await service.text_json(
            purpose=ModelPurpose.MEAL_SCAN,
            user_prompt="test",
            system_prompt="system",
        )

        call_kwargs = service._call_text.call_args.kwargs
        assert call_kwargs["model"] == "gemini-2.5-flash-lite"


class TestVision:
    @pytest.mark.asyncio
    async def test_vision_success(self, service):
        service._call_vision = AsyncMock(return_value={"result": "vision_success"})

        result = await service.vision(
            purpose=ModelPurpose.MEAL_SCAN,
            image_bytes=b"fake_image",
            prompt="analyze",
        )
        assert result == {"result": "vision_success"}

    @pytest.mark.asyncio
    async def test_vision_forwards_schema(self, service):
        class DummyVisionResponse(BaseModel):
            result: str

        service._call_vision = AsyncMock(return_value={"result": "ok"})

        await service.vision(
            purpose=ModelPurpose.MEAL_SCAN,
            image_bytes=b"fake_image",
            prompt="analyze",
            system_prompt="system",
            schema=DummyVisionResponse,
        )

        call_kwargs = service._call_vision.call_args.kwargs
        assert call_kwargs["schema"] is DummyVisionResponse
        assert call_kwargs["purpose_hint"] == "meal_scan"

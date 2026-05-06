import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.infra.services.ai.ai_model_manager import AIModelManager, ModelPurpose
from src.infra.services.ai.provider_circuit_breaker import CircuitState
from src.domain.exceptions.ai_exceptions import AIUnavailableError


@pytest.fixture
def mock_gemini_provider():
    from src.domain.ports.ai_provider_port import AICapability
    provider = Mock()
    provider.provider_name = "gemini"
    provider.get_available_models.return_value = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    provider.supported_capabilities = {AICapability.TEXT_GENERATION, AICapability.VISION, AICapability.STRUCTURED_OUTPUT}
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
    with patch(
        "src.infra.services.ai.ai_model_manager.GeminiProvider",
        return_value=mock_gemini_provider,
    ):
        with patch(
            "src.infra.services.ai.ai_model_manager.ProviderCircuitBreaker",
            return_value=mock_circuit_breaker,
        ):
            return AIModelManager()


class TestModelSelection:
    def test_get_fallback_chain_for_meal_scan(self, manager):
        chain = manager.get_fallback_chain(ModelPurpose.MEAL_SCAN)
        assert chain[0] == "gemini-2.5-flash"
        assert chain[1] == "gemini-2.5-flash-lite"

    def test_get_fallback_chain_for_barcode(self, manager):
        chain = manager.get_fallback_chain(ModelPurpose.BARCODE)
        assert chain[0] == "gemini-2.5-flash-lite"
        assert chain[1] == "gemini-2.5-flash"


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


class TestVision:
    @pytest.mark.asyncio
    async def test_generate_with_vision(self, manager, mock_gemini_provider):
        result = await manager.generate_with_vision(
            purpose=ModelPurpose.MEAL_SCAN,
            prompt="analyze",
            image_data=b"fake_image",
        )
        assert result == {"result": "vision_success"}

from unittest.mock import AsyncMock, Mock, patch

import pytest

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
    with patch(
        "src.infra.services.ai.ai_model_manager.GeminiProvider",
        return_value=mock_gemini_provider,
    ), patch(
        "src.infra.services.ai.ai_model_manager.ProviderCircuitBreaker",
        return_value=mock_circuit_breaker,
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
        assert mock_gemini_provider.generate.call_args_list[1].kwargs["cache_name"] is None
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


# ---------------------------------------------------------------------------
# Workers AI routing (TDD — fail until Phase 3 is implemented)
# ---------------------------------------------------------------------------

def _make_cf_settings():
    s = Mock()
    s.CLOUDFLARE_WORKERS_AI_ENABLED = True
    s.CLOUDFLARE_ACCOUNT_ID = "fake_account_id"
    s.CLOUDFLARE_API_TOKEN = "fake_api_token"
    s.CLOUDFLARE_AI_GATEWAY_ID = "fake_gateway"
    s.CLOUDFLARE_WORKERS_AI_TEXT_MODEL = "@cf/google/gemma-4-26b-a4b-it"
    s.CLOUDFLARE_WORKERS_AI_TEXT_PURPOSES = "recipe,general,meal_names,discovery"
    s.CLOUDFLARE_WORKERS_AI_JSON_MODE = True
    s.CLOUDFLARE_WORKERS_AI_TIMEOUT_SECONDS = 30
    return s


def _make_disabled_cf_settings():
    s = Mock()
    s.CLOUDFLARE_WORKERS_AI_ENABLED = False
    s.CLOUDFLARE_ACCOUNT_ID = ""
    s.CLOUDFLARE_API_TOKEN = ""
    s.CLOUDFLARE_AI_GATEWAY_ID = ""
    s.CLOUDFLARE_WORKERS_AI_TEXT_MODEL = ""
    s.CLOUDFLARE_WORKERS_AI_TEXT_PURPOSES = ""
    s.CLOUDFLARE_WORKERS_AI_JSON_MODE = False
    s.CLOUDFLARE_WORKERS_AI_TIMEOUT_SECONDS = 30
    return s


@pytest.fixture
def mock_cf_provider():
    from src.domain.ports.ai_provider_port import AICapability

    p = Mock()
    p.provider_name = "cloudflare-workers-ai"
    p.get_available_models.return_value = ["@cf/google/gemma-4-26b-a4b-it"]
    p.supported_capabilities = {AICapability.TEXT_GENERATION, AICapability.STRUCTURED_OUTPUT}
    p.generate = AsyncMock(return_value={"result": "cf_success"})
    p.extract_error_code = Mock(return_value=None)
    return p


@pytest.fixture
def manager_with_cf(mock_gemini_provider, mock_circuit_breaker, mock_cf_provider):
    """Manager with Cloudflare Workers AI enabled via settings injection."""
    with patch(
        "src.infra.services.ai.ai_model_manager.GeminiProvider",
        return_value=mock_gemini_provider,
    ), patch(
        "src.infra.services.ai.ai_model_manager.ProviderCircuitBreaker",
        return_value=mock_circuit_breaker,
    ), patch(
        "src.infra.services.ai.ai_model_manager.CloudflareWorkersAIProvider",
        create=True,
        return_value=mock_cf_provider,
    ):
        return AIModelManager(settings=_make_cf_settings())


@pytest.fixture
def manager_cf_disabled(mock_gemini_provider, mock_circuit_breaker):
    """Manager with Cloudflare explicitly disabled via settings injection."""
    with patch(
        "src.infra.services.ai.ai_model_manager.GeminiProvider",
        return_value=mock_gemini_provider,
    ), patch(
        "src.infra.services.ai.ai_model_manager.ProviderCircuitBreaker",
        return_value=mock_circuit_breaker,
    ):
        return AIModelManager(settings=_make_disabled_cf_settings())


class TestWorkersAIRouting:
    def test_workers_ai_absent_when_disabled(self, manager_cf_disabled):
        """All fallback chains are Gemini-only when CF is disabled."""
        for purpose in ModelPurpose:
            chain = manager_cf_disabled.get_fallback_chain(purpose)
            assert not any("@cf/" in m for m in chain), (
                f"{purpose.value} chain must not contain CF models when CF is disabled"
            )

    def test_text_purposes_get_cf_model_when_enabled(self, manager_with_cf):
        """Configured text purposes append the raw CF model id at the end of chain."""
        cf_alias = "@cf/google/gemma-4-26b-a4b-it"
        for purpose in (
            ModelPurpose.RECIPE,
            ModelPurpose.GENERAL,
            ModelPurpose.MEAL_NAMES,
            ModelPurpose.DISCOVERY,
        ):
            chain = manager_with_cf.get_fallback_chain(purpose)
            assert chain[-1] == cf_alias, (
                f"{purpose.value} chain should end with {cf_alias}, got {chain}"
            )
            # Gemini models still lead
            assert chain[0] == "gemini-2.5-flash-lite"
            assert chain[1] == "gemini-2.5-flash"

    def test_vision_purposes_stay_gemini_only_when_cf_enabled(self, manager_with_cf):
        """MEAL_SCAN and INGREDIENT_SCAN chains never include Workers AI."""
        for purpose in (ModelPurpose.MEAL_SCAN, ModelPurpose.INGREDIENT_SCAN):
            chain = manager_with_cf.get_fallback_chain(purpose)
            assert chain == ["gemini-2.5-flash-lite", "gemini-2.5-flash"], (
                f"{purpose.value} must remain Gemini-only even when CF is enabled"
            )

    def test_parse_text_stays_gemini_only_by_default(self, manager_with_cf):
        """PARSE_TEXT is not in the default CF text purposes; chain stays Gemini-only."""
        chain = manager_with_cf.get_fallback_chain(ModelPurpose.PARSE_TEXT)
        assert not any("@cf/" in m for m in chain)

    def test_barcode_stays_gemini_only_by_default(self, manager_with_cf):
        """BARCODE is not in the default CF text purposes; chain stays Gemini-only."""
        chain = manager_with_cf.get_fallback_chain(ModelPurpose.BARCODE)
        assert not any("@cf/" in m for m in chain)

    def test_cf_provider_registered_in_providers_when_enabled(self, manager_with_cf):
        """CloudflareWorkersAIProvider is wired into manager._providers when enabled."""
        assert "cloudflare-workers-ai" in manager_with_cf._providers

    def test_cf_provider_absent_from_providers_when_disabled(self, manager_cf_disabled):
        """No cloudflare-workers-ai key in _providers when CF is disabled."""
        assert "cloudflare-workers-ai" not in manager_cf_disabled._providers

    @pytest.mark.asyncio
    async def test_get_cache_name_returns_none_for_cf_model(self, manager_with_cf):
        """Gemini context cache must never be returned for a raw CF model id."""
        cache_mgr = Mock()
        cache_mgr.get_cache_name_for_model = AsyncMock(return_value="cachedContents/x")
        manager_with_cf.set_cache_manager(cache_mgr)

        result = await manager_with_cf._get_cache_name_for_model(
            "recipe", "@cf/google/gemma-4-26b-a4b-it"
        )
        assert result is None


class TestWorkersAIFallback:
    @pytest.mark.asyncio
    async def test_falls_through_to_cf_when_both_gemini_fail(
        self, manager_with_cf, mock_gemini_provider, mock_circuit_breaker, mock_cf_provider
    ):
        """When both Gemini models fail, Workers AI is tried and succeeds."""
        mock_gemini_provider.generate = AsyncMock(side_effect=Exception("503 UNAVAILABLE"))
        mock_circuit_breaker.filter_available = Mock(
            side_effect=lambda models: models
        )

        result = await manager_with_cf.generate(
            purpose=ModelPurpose.RECIPE,
            prompt="test",
            system_message="system",
        )

        assert result == {"result": "cf_success"}
        mock_cf_provider.generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cf_not_tried_for_vision_purpose(
        self, manager_with_cf, mock_gemini_provider, mock_cf_provider
    ):
        """Workers AI must not be attempted for MEAL_SCAN even when Gemini fails."""
        mock_gemini_provider.generate_with_vision = AsyncMock(
            side_effect=Exception("503 UNAVAILABLE")
        )

        from src.domain.exceptions.ai_exceptions import AIUnavailableError

        with pytest.raises(AIUnavailableError):
            await manager_with_cf.generate_with_vision(
                purpose=ModelPurpose.MEAL_SCAN,
                prompt="test",
                image_data=b"fake_image",
            )

        mock_cf_provider.generate.assert_not_awaited()
        mock_cf_provider.generate_with_vision = AsyncMock()
        mock_cf_provider.generate_with_vision.assert_not_awaited()

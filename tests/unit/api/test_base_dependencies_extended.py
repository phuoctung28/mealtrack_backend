"""Exercise remaining src.api.base_dependencies getters and factories (coverage)."""
import importlib
from unittest.mock import MagicMock, patch

import pytest

import src.api.base_dependencies as deps


@pytest.fixture(autouse=True)
def reset_subscription_singleton(monkeypatch):
    """Avoid leaking RevenueCatAdapter across tests."""
    monkeypatch.setattr(deps, "_subscription_service", None, raising=False)
    yield


def test_get_db_yields_from_config(monkeypatch):
    m = importlib.reload(deps)
    sent = object()

    def fake_cfg():
        yield sent

    monkeypatch.setattr(m, "get_db_from_config", fake_cfg)
    g = m.get_db()
    assert next(g) is sent


def test_get_image_store_singleton(monkeypatch):
    m = importlib.reload(deps)
    monkeypatch.setattr(m, "_image_store", None, raising=False)
    store = MagicMock()
    monkeypatch.setattr(m, "CloudinaryImageStore", lambda: store)
    assert m.get_image_store() is store
    assert m.get_image_store() is store


def test_get_vision_service_singleton(monkeypatch):
    m = importlib.reload(deps)
    monkeypatch.setattr(m, "_vision_service", None, raising=False)
    vs = MagicMock()
    monkeypatch.setattr(m, "VisionAIService", lambda: vs)
    assert m.get_vision_service() is vs
    assert m.get_vision_service() is vs


def test_get_ai_chat_service_success(monkeypatch):
    m = importlib.reload(deps)
    monkeypatch.setattr(m, "_ai_chat_service", None, raising=False)
    chat = MagicMock()
    monkeypatch.setattr(
        m,
        "GeminiChatService",
        lambda: chat,
        raising=False,
    )
    import types
    import sys

    sys.modules["src.infra.services.ai.gemini_chat_service"] = types.SimpleNamespace(
        GeminiChatService=lambda: chat
    )
    assert m.get_ai_chat_service() is chat
    assert m.get_ai_chat_service() is chat


def test_get_gpt_parser_get_food_mapping_get_food_data():
    m = importlib.reload(deps)
    assert m.get_gpt_parser() is not None
    assert m.get_food_mapping_service() is not None
    assert m.get_food_data_service() is not None


def test_get_food_cache_service_uses_cache_global(monkeypatch):
    m = importlib.reload(deps)
    monkeypatch.setattr(m, "_cache_service", object(), raising=False)
    fcs = m.get_food_cache_service()
    assert fcs is not None


def test_get_cache_service_and_monitor():
    m = importlib.reload(deps)
    assert m.get_cache_service() is m._cache_service
    assert m.get_cache_monitor() is m._cache_monitor


def test_get_open_food_facts_and_fat_secret(monkeypatch):
    m = importlib.reload(deps)
    monkeypatch.setattr(
        m,
        "get_open_food_facts_service",
        lambda: MagicMock(name="off"),
    )
    assert m.get_open_food_facts_service_instance() is not None

    with patch("src.infra.adapters.fat_secret_service.get_fat_secret_service") as gfs:
        gfs.return_value = MagicMock(name="fat")
        assert m.get_fat_secret_service_instance() is not None


def test_get_food_reference_repository_singleton(monkeypatch):
    m = importlib.reload(deps)
    monkeypatch.setattr(m, "_food_reference_repository", None, raising=False)
    repo = MagicMock()
    with patch(
        "src.infra.repositories.food_reference_repository.FoodReferenceRepository",
        return_value=repo,
    ):
        assert m.get_food_reference_repository() is repo
        assert m.get_barcode_product_repository() is repo


def test_get_notification_repository_and_service():
    m = importlib.reload(deps)
    db = MagicMock()
    nr = m.get_notification_repository(db=db)
    assert nr is not None
    ns = m.get_notification_service(
        notification_repository=MagicMock(),
        firebase_service=MagicMock(),
    )
    assert ns is not None


def test_get_scheduled_notification_service_before_init():
    m = importlib.reload(deps)
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(m, "_scheduled_notification_service", None, raising=False)
        assert m.get_scheduled_notification_service() is None
    finally:
        monkeypatch.undo()


def test_initialize_scheduled_notification_service(monkeypatch):
    m = importlib.reload(deps)
    monkeypatch.setattr(m, "_scheduled_notification_service", None, raising=False)
    sched = MagicMock()
    with patch.object(m, "NotificationRepository", return_value=MagicMock()), patch.object(
        m, "get_firebase_service", return_value=MagicMock()
    ), patch.object(m, "NotificationService", return_value=MagicMock()), patch.object(
        m, "ScheduledNotificationService", return_value=sched
    ):
        out = m.initialize_scheduled_notification_service()
    assert out is sched


def test_get_redis_client():
    m = importlib.reload(deps)
    assert m.get_redis_client() is m._redis_client


def test_get_meal_suggestion_repository_requires_redis(monkeypatch):
    m = importlib.reload(deps)
    monkeypatch.setattr(m, "_redis_client", None, raising=False)
    with pytest.raises(RuntimeError, match="Redis client not initialized"):
        m.get_meal_suggestion_repository()


def test_get_deepl_suggestion_with_key_builds_singleton(monkeypatch):
    m = importlib.reload(deps)
    monkeypatch.setattr(m, "_deepl_suggestion_translation_service", None, raising=False)
    monkeypatch.setattr(m.settings, "DEEPL_API_KEY", "k-test", raising=False)
    svc = MagicMock()
    adapter = MagicMock()
    with patch(
        "src.domain.services.meal_suggestion.deepl_suggestion_translation_service.DeepLSuggestionTranslationService",
        return_value=svc,
    ), patch(
        "src.infra.adapters.deepl_translation_adapter.DeepLTranslationAdapter",
        return_value=adapter,
    ):
        assert m.get_deepl_suggestion_translation_service() is svc
        assert m.get_deepl_suggestion_translation_service() is svc


def test_get_deepl_meal_translation_with_key(monkeypatch):
    m = importlib.reload(deps)
    monkeypatch.setattr(m, "_deepl_meal_translation_service", None, raising=False)
    monkeypatch.setattr(m.settings, "DEEPL_API_KEY", "k-test", raising=False)
    svc = MagicMock()
    with patch(
        "src.domain.services.meal_analysis.deepl_meal_translation_service.DeepLMealTranslationService",
        return_value=svc,
    ), patch(
        "src.infra.repositories.meal_translation_repository.MealTranslationRepository",
        return_value=MagicMock(),
    ), patch(
        "src.infra.adapters.deepl_translation_adapter.DeepLTranslationAdapter",
        return_value=MagicMock(),
    ):
        assert m.get_deepl_meal_translation_service() is svc


def test_get_subscription_service_singleton(monkeypatch):
    m = importlib.reload(deps)
    monkeypatch.setattr(m, "_subscription_service", None, raising=False)
    rc = MagicMock()
    with patch(
        "src.infra.adapters.revenuecat_adapter.RevenueCatAdapter",
        return_value=rc,
    ):
        assert m.get_subscription_service() is rc
        assert m.get_subscription_service() is rc


def test_get_suggestion_orchestration_service(monkeypatch):
    m = importlib.reload(deps)
    monkeypatch.setattr(m, "get_meal_suggestion_repository", lambda: MagicMock())
    monkeypatch.setattr(m, "get_deepl_suggestion_translation_service", lambda: None)
    orch = MagicMock()
    with patch(
        "src.infra.adapters.meal_generation_service.MealGenerationService",
        return_value=MagicMock(),
    ), patch(
        "src.domain.services.meal_suggestion.suggestion_orchestration_service.SuggestionOrchestrationService",
        return_value=orch,
    ), patch("src.infra.database.uow.UnitOfWork"):
        assert m.get_suggestion_orchestration_service() is orch

import importlib

import pytest


@pytest.mark.asyncio
async def test_initialize_cache_layer_noop_when_disabled(monkeypatch):
    deps = importlib.import_module("src.api.base_dependencies")
    monkeypatch.setattr(deps.settings, "CACHE_ENABLED", False, raising=False)

    # Should early-return without creating redis client
    await deps.initialize_cache_layer()
    assert getattr(deps, "_redis_client") is None


@pytest.mark.asyncio
async def test_initialize_cache_layer_creates_client_and_cache_service(monkeypatch):
    deps = importlib.import_module("src.api.base_dependencies")

    # Reset globals
    monkeypatch.setattr(deps, "_redis_client", None, raising=False)
    monkeypatch.setattr(deps, "_cache_service", None, raising=False)

    monkeypatch.setattr(deps.settings, "CACHE_ENABLED", True, raising=False)
    monkeypatch.setattr(deps.settings, "REDIS_MAX_CONNECTIONS", 1, raising=False)
    monkeypatch.setattr(deps.settings, "CACHE_DEFAULT_TTL", 60, raising=False)

    class _Redis:
        def __init__(self, redis_url, max_connections):
            # `settings.redis_url` may be a read-only computed property; we accept whatever.
            self.redis_url = str(redis_url)
            self.max_connections = max_connections
            self.connected = False

        async def connect(self):
            self.connected = True

        async def disconnect(self):
            self.connected = False

    class _Cache:
        def __init__(self, redis_client, default_ttl, monitor, enabled):
            self.redis_client = redis_client
            self.default_ttl = default_ttl
            self.enabled = enabled

    monkeypatch.setattr(deps, "RedisClient", _Redis)
    monkeypatch.setattr(deps, "CacheService", _Cache)

    await deps.initialize_cache_layer()
    assert deps._redis_client is not None
    assert deps._cache_service is not None
    assert deps._redis_client.connected is True


@pytest.mark.asyncio
async def test_shutdown_cache_layer_disconnects(monkeypatch):
    deps = importlib.import_module("src.api.base_dependencies")

    class _Redis:
        def __init__(self):
            self.disconnected = False

        async def disconnect(self):
            self.disconnected = True

    redis = _Redis()
    monkeypatch.setattr(deps, "_redis_client", redis, raising=False)
    monkeypatch.setattr(deps, "_cache_service", object(), raising=False)

    await deps.shutdown_cache_layer()
    assert deps._redis_client is None
    assert deps._cache_service is None
    assert redis.disconnected is True


def test_get_ai_chat_service_wraps_value_error(monkeypatch):
    deps = importlib.import_module("src.api.base_dependencies")
    monkeypatch.setattr(deps, "_ai_chat_service", None, raising=False)

    class _Gemini:
        def __init__(self):
            raise ValueError("missing key")

    monkeypatch.setattr(
        deps,
        "GeminiChatService",
        _Gemini,
        raising=False,  # imported inside function; we patch via sys.modules trick below
    )

    # Patch the import inside get_ai_chat_service to return our _Gemini
    import types, sys

    m = types.SimpleNamespace(GeminiChatService=_Gemini)
    sys.modules["src.infra.services.ai.gemini_chat_service"] = m

    with pytest.raises(ValueError) as exc:
        deps.get_ai_chat_service()
    assert "GOOGLE_API_KEY" in str(exc.value)


def test_get_deepl_meal_translation_service_returns_none_without_key(monkeypatch):
    deps = importlib.import_module("src.api.base_dependencies")
    monkeypatch.setattr(deps, "_deepl_meal_translation_service", None, raising=False)
    monkeypatch.setattr(deps.settings, "DEEPL_API_KEY", "", raising=False)
    assert deps.get_deepl_meal_translation_service() is None


def test_get_deepl_suggestion_translation_service_returns_none_without_key(monkeypatch):
    deps = importlib.import_module("src.api.base_dependencies")
    monkeypatch.setattr(deps, "_deepl_suggestion_translation_service", None, raising=False)
    monkeypatch.setattr(deps.settings, "DEEPL_API_KEY", "", raising=False)
    assert deps.get_deepl_suggestion_translation_service() is None


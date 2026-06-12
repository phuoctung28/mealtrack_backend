"""Feature flag routes with mocked DB session and optional cache."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.base_dependencies import get_cache_service
from src.api.dependencies.auth import get_current_user_email, require_admin
from src.api.routes.v1.feature_flags import router
from src.infra.database.config_async import get_async_db
from src.infra.database.models.feature_flag import FeatureFlag


def _make_flag(name="beta", enabled=True):
    f = MagicMock(spec=FeatureFlag)
    f.name = name
    f.enabled = enabled
    f.description = "d"
    f.created_at = datetime(2024, 1, 1)
    f.updated_at = datetime(2024, 1, 2)
    return f


def _async_session_for_results(results):
    scalars = MagicMock()
    scalars.all.return_value = results

    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars
    execute_result.scalar_one_or_none.return_value = results[0] if results else None

    session = MagicMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def app_no_cache():
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_cache_service] = lambda: None
    # Business-logic tests bypass the admin gate; the gate itself is covered by
    # the dedicated admin tests at the bottom of this file.
    application.dependency_overrides[require_admin] = lambda: "admin@test.local"
    return application


def test_get_feature_flags_empty_db(app_no_cache):
    session = _async_session_for_results([])
    app_no_cache.dependency_overrides[get_async_db] = lambda: session

    r = TestClient(app_no_cache).get("/v1/feature-flags/")
    assert r.status_code == 200
    assert r.json()["flags"] == {}
    app_no_cache.dependency_overrides = {}


def test_get_feature_flags_cache_miss_then_set_json(app_no_cache):
    """Covers cache set after DB read (lines ~49–51)."""
    cache = AsyncMock()
    cache.get_json = AsyncMock(return_value=None)
    cache.set_json = AsyncMock()
    app_no_cache.dependency_overrides[get_cache_service] = lambda: cache

    session = _async_session_for_results([])
    app_no_cache.dependency_overrides[get_async_db] = lambda: session

    r = TestClient(app_no_cache).get("/v1/feature-flags/")
    assert r.status_code == 200
    cache.set_json.assert_awaited()
    app_no_cache.dependency_overrides = {}


def test_get_individual_flag_cache_miss_then_set_json(app_no_cache):
    """Covers per-flag cache set (lines ~90–91)."""
    cache = AsyncMock()
    cache.get_json = AsyncMock(return_value=None)
    cache.set_json = AsyncMock()
    app_no_cache.dependency_overrides[get_cache_service] = lambda: cache

    flag = _make_flag()
    session = _async_session_for_results([flag])
    app_no_cache.dependency_overrides[get_async_db] = lambda: session

    r = TestClient(app_no_cache).get("/v1/feature-flags/beta")
    assert r.status_code == 200
    cache.set_json.assert_awaited()
    app_no_cache.dependency_overrides = {}


def test_get_feature_flags_uses_cache_hit(app_no_cache):
    cache = AsyncMock()
    cache.get_json = AsyncMock(
        return_value={"flags": {"x": True}, "updated_at": "2024-01-01T00:00:00"}
    )
    app_no_cache.dependency_overrides[get_cache_service] = lambda: cache

    session = _async_session_for_results([])
    app_no_cache.dependency_overrides[get_async_db] = lambda: session

    r = TestClient(app_no_cache).get("/v1/feature-flags/")
    assert r.status_code == 200
    assert r.json()["flags"]["x"] is True
    session.execute.assert_not_awaited()
    app_no_cache.dependency_overrides = {}


def test_get_individual_flag_not_found(app_no_cache):
    session = _async_session_for_results([])
    app_no_cache.dependency_overrides[get_async_db] = lambda: session

    r = TestClient(app_no_cache).get("/v1/feature-flags/missing")
    assert r.status_code == 404
    app_no_cache.dependency_overrides = {}


def test_get_individual_flag_found_and_cache_set(app_no_cache):
    flag = _make_flag()
    session = _async_session_for_results([flag])
    app_no_cache.dependency_overrides[get_async_db] = lambda: session

    cache = AsyncMock()
    cache.get_json = AsyncMock(return_value=None)
    cache.set_json = AsyncMock()
    app_no_cache.dependency_overrides[get_cache_service] = lambda: cache

    r = TestClient(app_no_cache).get("/v1/feature-flags/beta")
    assert r.status_code == 200
    assert r.json()["name"] == "beta"
    cache.set_json.assert_awaited()
    app_no_cache.dependency_overrides = {}


def test_create_feature_flag_success(app_no_cache):
    new_flag = _make_flag(name="new_flag", enabled=False)
    new_flag.created_at = datetime(2024, 6, 1, tzinfo=None)

    cache = AsyncMock()
    app_no_cache.dependency_overrides[get_cache_service] = lambda: cache

    with patch(
        "src.api.routes.v1.feature_flags.FeatureFlagService.create",
        new=AsyncMock(return_value=new_flag),
    ):
        r = TestClient(app_no_cache).post(
            "/v1/feature-flags/",
            json={"name": "new_flag", "enabled": False, "description": "x"},
        )
    assert r.status_code == 201
    cache.invalidate.assert_awaited()
    app_no_cache.dependency_overrides = {}


def test_create_feature_flag_conflict(app_no_cache):
    from fastapi import HTTPException

    with patch(
        "src.api.routes.v1.feature_flags.FeatureFlagService.create",
        new=AsyncMock(side_effect=HTTPException(status_code=409, detail="already exists")),
    ):
        r = TestClient(app_no_cache).post(
            "/v1/feature-flags/",
            json={"name": "beta", "enabled": True},
        )
    assert r.status_code == 409
    app_no_cache.dependency_overrides = {}


def test_update_feature_flag_success(app_no_cache):
    flag = _make_flag()
    flag.updated_at = datetime(2024, 1, 3)

    cache = AsyncMock()
    app_no_cache.dependency_overrides[get_cache_service] = lambda: cache

    with patch(
        "src.api.routes.v1.feature_flags.FeatureFlagService.update",
        new=AsyncMock(return_value=flag),
    ):
        r = TestClient(app_no_cache).put(
            "/v1/feature-flags/beta",
            json={"enabled": False, "description": "new desc"},
        )
    assert r.status_code == 200
    cache.invalidate.assert_awaited()
    app_no_cache.dependency_overrides = {}


def test_update_feature_flag_not_found(app_no_cache):
    from fastapi import HTTPException

    with patch(
        "src.api.routes.v1.feature_flags.FeatureFlagService.update",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail="not found")),
    ):
        r = TestClient(app_no_cache).put(
            "/v1/feature-flags/ghost",
            json={"enabled": True},
        )
    assert r.status_code == 404
    app_no_cache.dependency_overrides = {}


def test_mutations_reject_non_admin(monkeypatch):
    """POST/PUT return 403 for an authenticated non-admin (empty allowlist)."""
    from src.api.dependencies import auth as auth_dep

    monkeypatch.setattr(auth_dep.settings, "ADMIN_EMAILS", "")
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_cache_service] = lambda: None
    application.dependency_overrides[get_async_db] = lambda: _async_session_for_results([])
    application.dependency_overrides[get_current_user_email] = (
        lambda: "stranger@example.com"
    )

    client = TestClient(application)
    assert (
        client.post(
            "/v1/feature-flags/", json={"name": "x", "enabled": True}
        ).status_code
        == 403
    )
    assert client.put("/v1/feature-flags/x", json={"enabled": True}).status_code == 403


def test_mutations_allow_configured_admin(monkeypatch):
    """A configured admin (case-insensitive) passes the gate and creates a flag."""
    from src.api.dependencies import auth as auth_dep

    monkeypatch.setattr(
        auth_dep.settings, "ADMIN_EMAILS", "boss@nutree.ai, admin@x.com"
    )
    new_flag = _make_flag(name="n", enabled=True)
    new_flag.created_at = datetime(2024, 6, 1)

    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_cache_service] = lambda: None
    application.dependency_overrides[get_current_user_email] = lambda: "Admin@X.com"

    with patch(
        "src.api.routes.v1.feature_flags.FeatureFlagService.create",
        new=AsyncMock(return_value=new_flag),
    ):
        r = TestClient(application).post(
            "/v1/feature-flags/", json={"name": "n", "enabled": True, "description": "d"}
        )
    assert r.status_code == 201

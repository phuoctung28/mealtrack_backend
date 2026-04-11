"""Feature flag routes with mocked DB session and optional cache."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.base_dependencies import get_cache_service, get_db
from src.api.routes.v1.feature_flags import router
from src.infra.database.models.feature_flag import FeatureFlag


def _make_flag(name="beta", enabled=True):
    f = MagicMock(spec=FeatureFlag)
    f.name = name
    f.enabled = enabled
    f.description = "d"
    f.created_at = datetime(2024, 1, 1)
    f.updated_at = datetime(2024, 1, 2)
    return f


@pytest.fixture
def app_no_cache():
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_cache_service] = lambda: None
    return application


def test_get_feature_flags_empty_db(app_no_cache):
    session = MagicMock()
    session.query.return_value.all.return_value = []
    app_no_cache.dependency_overrides[get_db] = lambda: session

    r = TestClient(app_no_cache).get("/v1/feature-flags/")
    assert r.status_code == 200
    assert r.json()["flags"] == {}
    app_no_cache.dependency_overrides = {}


def test_get_feature_flags_uses_cache_hit(app_no_cache):
    cache = AsyncMock()
    cache.get_json = AsyncMock(
        return_value={"flags": {"x": True}, "updated_at": "2024-01-01T00:00:00"}
    )
    app_no_cache.dependency_overrides[get_cache_service] = lambda: cache

    session = MagicMock()
    app_no_cache.dependency_overrides[get_db] = lambda: session

    r = TestClient(app_no_cache).get("/v1/feature-flags/")
    assert r.status_code == 200
    assert r.json()["flags"]["x"] is True
    session.query.assert_not_called()
    app_no_cache.dependency_overrides = {}


def test_get_individual_flag_not_found(app_no_cache):
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    app_no_cache.dependency_overrides[get_db] = lambda: session

    r = TestClient(app_no_cache).get("/v1/feature-flags/missing")
    assert r.status_code == 404
    app_no_cache.dependency_overrides = {}


def test_get_individual_flag_found_and_cache_set(app_no_cache):
    flag = _make_flag()
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = flag
    app_no_cache.dependency_overrides[get_db] = lambda: session

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
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None

    def refresh_side_effect(obj):
        obj.created_at = datetime(2024, 6, 1, tzinfo=None)

    session.refresh.side_effect = refresh_side_effect
    app_no_cache.dependency_overrides[get_db] = lambda: session

    cache = AsyncMock()
    app_no_cache.dependency_overrides[get_cache_service] = lambda: cache

    r = TestClient(app_no_cache).post(
        "/v1/feature-flags/",
        json={"name": "new_flag", "enabled": False, "description": "x"},
    )
    assert r.status_code == 201
    session.add.assert_called_once()
    session.commit.assert_called_once()
    cache.invalidate.assert_awaited()
    app_no_cache.dependency_overrides = {}


def test_create_feature_flag_conflict(app_no_cache):
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = _make_flag()
    app_no_cache.dependency_overrides[get_db] = lambda: session

    r = TestClient(app_no_cache).post(
        "/v1/feature-flags/",
        json={"name": "beta", "enabled": True},
    )
    assert r.status_code == 409
    app_no_cache.dependency_overrides = {}


def test_update_feature_flag_success(app_no_cache):
    flag = _make_flag()
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = flag
    app_no_cache.dependency_overrides[get_db] = lambda: session

    cache = AsyncMock()
    app_no_cache.dependency_overrides[get_cache_service] = lambda: cache

    r = TestClient(app_no_cache).put(
        "/v1/feature-flags/beta",
        json={"enabled": False, "description": "new desc"},
    )
    assert r.status_code == 200
    assert flag.enabled is False
    assert flag.description == "new desc"
    session.commit.assert_called_once()
    cache.invalidate.assert_awaited()
    app_no_cache.dependency_overrides = {}


def test_update_feature_flag_not_found(app_no_cache):
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    app_no_cache.dependency_overrides[get_db] = lambda: session

    r = TestClient(app_no_cache).put(
        "/v1/feature-flags/ghost",
        json={"enabled": True},
    )
    assert r.status_code == 404
    app_no_cache.dependency_overrides = {}

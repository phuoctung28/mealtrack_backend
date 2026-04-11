"""Exercise health router endpoints with mocked engine / DB / Firebase."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.v1 import health as health_mod


@pytest.fixture
def health_client():
    app = FastAPI()
    app.include_router(health_mod.router)
    return TestClient(app)


def test_health_check(health_client):
    r = health_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_root(health_client):
    r = health_client.get("/")
    assert r.status_code == 200
    assert r.json()["name"] == "MealTrack API"


def test_database_pool_status_ok(monkeypatch):
    pool = MagicMock()
    pool.checkedout.return_value = 2
    pool.size.return_value = 10
    pool.overflow.return_value = 1
    engine = MagicMock()
    engine.pool = pool

    app = FastAPI()
    app.include_router(health_mod.router)
    monkeypatch.setattr(health_mod, "engine", engine)

    r = TestClient(app).get("/health/db-pool")
    assert r.status_code == 200
    body = r.json()
    assert body["checked_out"] == 2
    assert body["utilization_pct"] == 20.0


def test_database_pool_status_error(monkeypatch):
    pool = MagicMock()
    pool.checkedout.side_effect = RuntimeError("pool broken")
    engine = MagicMock()
    engine.pool = pool
    app = FastAPI()
    app.include_router(health_mod.router)
    monkeypatch.setattr(health_mod, "engine", engine)

    r = TestClient(app).get("/health/db-pool")
    assert r.status_code == 503
    assert "pool broken" in r.json()["error"]


@pytest.mark.asyncio
async def test_fetch_mysql_connection_stats_with_username(monkeypatch):
    conn = MagicMock()
    row_active = MagicMock()
    row_active.scalar_one.return_value = 5
    row_max = ("max_connections", "151")

    def exec_side_effect(stmt, params=None):
        sql = str(stmt)
        if "information_schema" in sql:
            assert params == {"user": "app"}
            return row_active
        if "SHOW VARIABLES" in sql:
            return MagicMock(fetchone=MagicMock(return_value=row_max))
        raise AssertionError(sql)

    conn.execute.side_effect = exec_side_effect
    cm = MagicMock()
    cm.__enter__.return_value = conn
    cm.__exit__.return_value = None

    engine = MagicMock()
    engine.url.username = "app"
    engine.connect.return_value = cm
    monkeypatch.setattr(health_mod, "engine", engine)

    stats = await health_mod._fetch_mysql_connection_stats()
    assert stats["active_connections"] == 5
    assert stats["max_connections"] == 151
    assert stats["utilization_pct"] is not None


@pytest.mark.asyncio
async def test_fetch_mysql_connection_stats_no_username(monkeypatch):
    conn = MagicMock()
    row_active = MagicMock()
    row_active.scalar_one.return_value = 3
    row_max = ("max_connections", "not_int")

    def exec_side_effect(stmt, params=None):
        sql = str(stmt)
        if "information_schema" in sql:
            assert params == {}
            return row_active
        return MagicMock(fetchone=MagicMock(return_value=row_max))

    conn.execute.side_effect = exec_side_effect
    cm = MagicMock()
    cm.__enter__.return_value = conn
    cm.__exit__.return_value = None

    engine = MagicMock()
    engine.url.username = None
    engine.connect.return_value = cm
    monkeypatch.setattr(health_mod, "engine", engine)

    stats = await health_mod._fetch_mysql_connection_stats()
    assert stats["active_connections"] == 3
    assert stats["max_connections"] is None
    assert stats["utilization_pct"] is None


def test_mysql_connection_status_ok(monkeypatch):
    app = FastAPI()
    app.include_router(health_mod.router)

    async def fake_stats():
        return {"active_connections": 1}

    monkeypatch.setattr(health_mod, "_fetch_mysql_connection_stats", fake_stats)
    r = TestClient(app).get("/health/mysql-connections")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_mysql_connection_status_error(monkeypatch):
    app = FastAPI()
    app.include_router(health_mod.router)

    async def boom():
        raise RuntimeError("db")

    monkeypatch.setattr(health_mod, "_fetch_mysql_connection_stats", boom)
    r = TestClient(app).get("/health/mysql-connections")
    assert r.status_code == 503


def _session_with_token_counts(total: int, active: int):
    q_total = MagicMock()
    q_total.scalar.return_value = total
    q_active = MagicMock()
    q_active.filter.return_value = q_active
    q_active.scalar.return_value = active
    session = MagicMock()
    session.query.side_effect = [q_total, q_active]
    return session


def test_notification_health_firebase_degraded(monkeypatch):
    app = FastAPI()
    app.include_router(health_mod.router)

    class _FB:
        def is_initialized(self):
            return False

    session = _session_with_token_counts(0, 0)

    with patch(
        "src.infra.services.firebase_service.FirebaseService",
        return_value=_FB(),
    ), patch(
        "src.infra.database.config.SessionLocal",
        return_value=session,
    ):
        r = TestClient(app).get("/health/notifications")

    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"


def test_notification_health_warning_high_inactive(monkeypatch):
    app = FastAPI()
    app.include_router(health_mod.router)

    class _FB:
        def is_initialized(self):
            return True

    session = _session_with_token_counts(10, 2)

    with patch(
        "src.infra.services.firebase_service.FirebaseService",
        return_value=_FB(),
    ), patch(
        "src.infra.database.config.SessionLocal",
        return_value=session,
    ):
        r = TestClient(app).get("/health/notifications")

    assert r.status_code == 503
    assert r.json()["status"] == "warning"


def test_notification_health_error(monkeypatch):
    app = FastAPI()
    app.include_router(health_mod.router)

    with patch(
        "src.infra.services.firebase_service.FirebaseService",
        side_effect=RuntimeError("boom"),
    ):
        r = TestClient(app).get("/health/notifications")
    assert r.status_code == 503
    assert "boom" in r.json()["error"]

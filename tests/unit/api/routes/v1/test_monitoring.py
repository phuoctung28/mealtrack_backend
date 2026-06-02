import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
import asyncio


def test_cache_metrics_returns_snapshot():
    from src.api.routes.v1.monitoring import cache_metrics

    mock_monitor = MagicMock()
    mock_monitor.snapshot.return_value = {"hits": 10, "misses": 5}

    result = asyncio.run(cache_metrics(cache_monitor=mock_monitor))

    assert result == {"hits": 10, "misses": 5}
    mock_monitor.snapshot.assert_called_once()


def test_cache_metrics_requires_monitoring_token(monkeypatch):
    """The endpoint is gated by the X-Monitoring-Token service token."""
    from fastapi import FastAPI
    from src.api.routes.v1.monitoring import router
    from src.api.base_dependencies import get_cache_monitor
    from src.api.dependencies import auth as auth_dep

    monkeypatch.setattr(auth_dep.settings, "MONITORING_API_TOKEN", "secret-token")

    app = FastAPI()
    app.include_router(router)
    mock_monitor = MagicMock()
    mock_monitor.snapshot.return_value = {"hits": 1, "misses": 0}
    app.dependency_overrides[get_cache_monitor] = lambda: mock_monitor
    client = TestClient(app)

    assert client.get("/v1/monitoring/cache/metrics").status_code == 403
    assert (
        client.get(
            "/v1/monitoring/cache/metrics", headers={"X-Monitoring-Token": "wrong"}
        ).status_code
        == 403
    )
    ok = client.get(
        "/v1/monitoring/cache/metrics",
        headers={"X-Monitoring-Token": "secret-token"},
    )
    assert ok.status_code == 200
    assert ok.json() == {"hits": 1, "misses": 0}

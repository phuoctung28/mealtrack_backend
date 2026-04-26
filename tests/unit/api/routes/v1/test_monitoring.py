import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def test_cache_metrics_returns_snapshot():
    from src.api.routes.v1.monitoring import cache_metrics

    mock_monitor = MagicMock()
    mock_monitor.snapshot.return_value = {"hits": 10, "misses": 5}

    import asyncio

    result = asyncio.get_event_loop().run_until_complete(
        cache_metrics(cache_monitor=mock_monitor)
    )

    assert result == {"hits": 10, "misses": 5}
    mock_monitor.snapshot.assert_called_once()

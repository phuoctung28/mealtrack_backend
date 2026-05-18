"""Integration tests for hydration API routes."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.main import app


@pytest.fixture
def client(test_session):
    """TestClient with auth and event_bus overridden; no real DB or Firebase needed."""
    import src.api.dependencies.event_bus as event_bus_module

    event_bus_module._configured_event_bus = None

    mock_bus = Mock()
    mock_bus.send = AsyncMock()

    app.dependency_overrides[get_current_user_id] = lambda: "test-user-id"
    app.dependency_overrides[get_configured_event_bus] = lambda: mock_bus

    with TestClient(app) as c:
        c._mock_bus = mock_bus
        yield c

    app.dependency_overrides.clear()
    event_bus_module._configured_event_bus = None


class TestHydrationRoutes:
    # ── POST /v1/hydration/log ────────────────────────────────────────────

    def test_log_hydration_returns_201(self, client):
        client._mock_bus.send = AsyncMock(
            return_value={
                "id": "uuid-h1",
                "drink_type": "WATER",
                "volume_ml": 500,
                "logged_at": "2026-05-18T08:00:00+00:00",
                "created_at": "2026-05-18T00:00:00+00:00",
            }
        )
        resp = client.post(
            "/v1/hydration/log",
            json={
                "drink_type": "WATER",
                "volume_ml": 500,
                "logged_at": "2026-05-18T08:00:00+00:00",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["drink_type"] == "WATER"
        assert data["volume_ml"] == 500

    def test_log_hydration_volume_above_2000_returns_422(self, client):
        """Pydantic rejects volume_ml > 2000."""
        resp = client.post(
            "/v1/hydration/log",
            json={
                "drink_type": "WATER",
                "volume_ml": 3000,
                "logged_at": "2026-05-18T08:00:00+00:00",
            },
        )
        assert resp.status_code == 422

    def test_log_hydration_volume_zero_returns_422(self, client):
        """Pydantic rejects volume_ml=0."""
        resp = client.post(
            "/v1/hydration/log",
            json={
                "drink_type": "WATER",
                "volume_ml": 0,
                "logged_at": "2026-05-18T08:00:00+00:00",
            },
        )
        assert resp.status_code == 422

    def test_log_hydration_missing_fields_returns_422(self, client):
        resp = client.post("/v1/hydration/log", json={"drink_type": "WATER"})
        assert resp.status_code == 422

    # ── GET /v1/hydration ─────────────────────────────────────────────────

    def test_get_hydration_returns_200_with_shape(self, client):
        client._mock_bus.send = AsyncMock(
            return_value={
                "date": "2026-05-18",
                "goal_ml": 2000,
                "total_ml": 750,
                "entries": [
                    {
                        "id": "uuid-h1",
                        "drink_type": "WATER",
                        "volume_ml": 500,
                        "logged_at": "2026-05-18T08:00:00+00:00",
                    },
                    {
                        "id": "uuid-h2",
                        "drink_type": "BLACK_COFFEE",
                        "volume_ml": 250,
                        "logged_at": "2026-05-18T09:00:00+00:00",
                    },
                ],
            }
        )
        resp = client.get("/v1/hydration?date=2026-05-18")
        assert resp.status_code == 200
        data = resp.json()
        assert data["goal_ml"] == 2000
        assert data["total_ml"] == 750
        assert len(data["entries"]) == 2

    def test_get_hydration_invalid_date_returns_400(self, client):
        resp = client.get("/v1/hydration?date=bad-date")
        assert resp.status_code == 400

    def test_get_hydration_no_date_defaults_to_today(self, client):
        client._mock_bus.send = AsyncMock(
            return_value={
                "date": "2026-05-18",
                "goal_ml": 2000,
                "total_ml": 0,
                "entries": [],
            }
        )
        resp = client.get("/v1/hydration")
        assert resp.status_code == 200

    # ── DELETE /v1/hydration/{id} ─────────────────────────────────────────

    def test_delete_hydration_returns_204(self, client):
        client._mock_bus.send = AsyncMock(return_value={"deleted": True})
        resp = client.delete("/v1/hydration/some-entry-id")
        assert resp.status_code == 204

    def test_delete_hydration_forbidden_returns_403(self, client):
        from src.api.exceptions import AuthorizationException

        client._mock_bus.send = AsyncMock(
            side_effect=AuthorizationException(
                message="Forbidden", error_code="HYDRATION_ENTRY_FORBIDDEN"
            )
        )
        resp = client.delete("/v1/hydration/other-user-entry")
        assert resp.status_code == 403

    def test_delete_hydration_not_found_returns_404(self, client):
        from src.api.exceptions import ResourceNotFoundException

        client._mock_bus.send = AsyncMock(
            side_effect=ResourceNotFoundException(
                message="Not found", error_code="HYDRATION_ENTRY_NOT_FOUND"
            )
        )
        resp = client.delete("/v1/hydration/nonexistent-entry")
        assert resp.status_code == 404

    # ── PATCH /v1/users/me/hydration-goal ────────────────────────────────

    def test_update_hydration_goal_returns_200(self, client):
        client._mock_bus.send = AsyncMock(return_value={"goal_ml": 2500})
        resp = client.patch("/v1/users/me/hydration-goal", json={"goal_ml": 2500})
        assert resp.status_code == 200
        assert resp.json()["goal_ml"] == 2500

    def test_update_hydration_goal_at_bounds(self, client):
        """500 and 4000 are accepted by Pydantic schema."""
        for goal in (500, 4000):
            client._mock_bus.send = AsyncMock(return_value={"goal_ml": goal})
            resp = client.patch(
                "/v1/users/me/hydration-goal", json={"goal_ml": goal}
            )
            assert resp.status_code == 200, f"Expected 200 for goal_ml={goal}"

    def test_update_hydration_goal_above_4000_returns_422(self, client):
        """4001 rejected by Pydantic schema (le=4000)."""
        for bad in (4001, 5000):
            resp = client.patch(
                "/v1/users/me/hydration-goal", json={"goal_ml": bad}
            )
            assert resp.status_code == 422, f"Expected 422 for goal_ml={bad}"

    def test_update_hydration_goal_below_500_returns_422(self, client):
        """100 and 0 rejected by Pydantic schema (ge=500)."""
        for bad in (0, 100, 499):
            resp = client.patch(
                "/v1/users/me/hydration-goal", json={"goal_ml": bad}
            )
            assert resp.status_code == 422, f"Expected 422 for goal_ml={bad}"

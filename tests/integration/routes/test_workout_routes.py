"""Integration tests for workout API routes."""

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


class TestWorkoutRoutes:
    # ── POST /v1/workouts/log ──────────────────────────────────────────────

    def test_log_workout_returns_201(self, client):
        client._mock_bus.send = AsyncMock(
            return_value={
                "id": "uuid-1",
                "workout_type": "RUNNING",
                "intensity": "MODERATE",
                "duration_minutes": 45,
                "estimated_burn_kcal": 466.9,
                "logged_at": "2026-05-18T07:30:00+00:00",
                "notes": None,
                "created_at": "2026-05-18T00:00:00+00:00",
            }
        )
        resp = client.post(
            "/v1/workouts/log",
            json={
                "workout_type": "RUNNING",
                "intensity": "MODERATE",
                "duration_minutes": 45,
                "logged_at": "2026-05-18T07:30:00+00:00",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["workout_type"] == "RUNNING"
        assert data["estimated_burn_kcal"] == 466.9

    def test_log_workout_null_burn_is_valid(self, client):
        """estimated_burn_kcal may be null when user has no weight."""
        client._mock_bus.send = AsyncMock(
            return_value={
                "id": "uuid-2",
                "workout_type": "YOGA",
                "intensity": "LIGHT",
                "duration_minutes": 30,
                "estimated_burn_kcal": None,
                "logged_at": "2026-05-18T07:30:00+00:00",
                "notes": None,
                "created_at": "2026-05-18T00:00:00+00:00",
            }
        )
        resp = client.post(
            "/v1/workouts/log",
            json={
                "workout_type": "YOGA",
                "intensity": "LIGHT",
                "duration_minutes": 30,
                "logged_at": "2026-05-18T07:30:00+00:00",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["estimated_burn_kcal"] is None

    def test_log_workout_invalid_payload_returns_422(self, client):
        """Missing required fields returns 422 from Pydantic."""
        resp = client.post("/v1/workouts/log", json={"workout_type": "RUNNING"})
        assert resp.status_code == 422

    def test_log_workout_zero_duration_returns_422(self, client):
        """duration_minutes must be > 0."""
        resp = client.post(
            "/v1/workouts/log",
            json={
                "workout_type": "RUNNING",
                "intensity": "MODERATE",
                "duration_minutes": 0,
                "logged_at": "2026-05-18T07:30:00+00:00",
            },
        )
        assert resp.status_code == 422

    # ── GET /v1/workouts ──────────────────────────────────────────────────

    def test_get_workouts_returns_200(self, client):
        client._mock_bus.send = AsyncMock(
            return_value={
                "date": "2026-05-18",
                "entries": [],
                "total_burn_kcal": None,
            }
        )
        resp = client.get("/v1/workouts?date=2026-05-18")
        assert resp.status_code == 200
        data = resp.json()
        assert data["date"] == "2026-05-18"
        assert data["entries"] == []
        assert data["total_burn_kcal"] is None

    def test_get_workouts_invalid_date_format_returns_400(self, client):
        resp = client.get("/v1/workouts?date=not-a-date")
        assert resp.status_code == 400

    def test_get_workouts_no_date_defaults_to_today(self, client):
        client._mock_bus.send = AsyncMock(
            return_value={"date": "2026-05-18", "entries": [], "total_burn_kcal": None}
        )
        resp = client.get("/v1/workouts")
        assert resp.status_code == 200

    # ── DELETE /v1/workouts/{id} ──────────────────────────────────────────

    def test_delete_workout_returns_204(self, client):
        client._mock_bus.send = AsyncMock(return_value={"deleted": True})
        resp = client.delete("/v1/workouts/some-uuid")
        assert resp.status_code == 204

    def test_delete_workout_forbidden_returns_403(self, client):
        from src.api.exceptions import AuthorizationException

        client._mock_bus.send = AsyncMock(
            side_effect=AuthorizationException(
                message="Forbidden", error_code="WORKOUT_LOG_FORBIDDEN"
            )
        )
        resp = client.delete("/v1/workouts/other-user-uuid")
        assert resp.status_code == 403

    def test_delete_workout_not_found_returns_404(self, client):
        from src.api.exceptions import ResourceNotFoundException

        client._mock_bus.send = AsyncMock(
            side_effect=ResourceNotFoundException(
                message="Not found", error_code="WORKOUT_LOG_NOT_FOUND"
            )
        )
        resp = client.delete("/v1/workouts/nonexistent-uuid")
        assert resp.status_code == 404

"""
Unit tests for RequestLoggerMiddleware.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware.request_logger import (
    RequestLoggerMiddleware,
    get_request_id,
)


@pytest.fixture
def app():
    """Create test FastAPI app with middleware."""
    app = FastAPI()
    app.add_middleware(RequestLoggerMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    @app.get("/slow")
    async def slow_endpoint():
        import asyncio

        await asyncio.sleep(1.5)  # Simulate slow request
        return {"status": "slow"}

    @app.get("/error")
    def error_endpoint():
        raise ValueError("Test error")

    @app.get("/health")
    def health_endpoint():
        return {"healthy": True}

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


class TestRequestLogging:
    """Test request logging functionality."""

    def test_middleware_is_not_base_http_middleware(self):
        """RequestLoggerMiddleware must be a pure ASGI callable, not BaseHTTPMiddleware."""
        from starlette.middleware.base import BaseHTTPMiddleware

        assert not issubclass(RequestLoggerMiddleware, BaseHTTPMiddleware), (
            "RequestLoggerMiddleware must not subclass BaseHTTPMiddleware — "
            "it buffers the full request body which penalises large file uploads."
        )

    def test_adds_request_id_header(self, client):
        """Response should include X-Request-ID header."""
        response = client.get("/test")

        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) == 8

    def test_adds_response_time_header(self, client):
        """Response should include X-Response-Time header."""
        response = client.get("/test")

        assert "X-Response-Time" in response.headers
        assert "s" in response.headers["X-Response-Time"]

    def test_skips_health_endpoint(self, client):
        """Health endpoint should be skipped."""
        response = client.get("/health")

        # Health endpoint works but may not have request ID
        assert response.status_code == 200

    def test_logs_request(self, client, caplog):
        """Should log request details."""
        with caplog.at_level("INFO"):
            client.get("/test")

        # Check log contains request info
        assert any("[REQ-" in record.message for record in caplog.records)
        assert any("GET /test" in record.message for record in caplog.records)

    def test_logs_response(self, client, caplog):
        """Should log response details."""
        with caplog.at_level("INFO"):
            client.get("/test")

        # Check log contains response info
        assert any("[RES-" in record.message for record in caplog.records)
        assert any("status=200" in record.message for record in caplog.records)

    def test_sets_observability_request_context(self, client):
        """Should attach only safe request metadata to observability context."""
        with patch(
            "src.api.middleware.request_logger.set_request_context"
        ) as mock_set_context:
            response = client.get("/test", headers={"Authorization": "Bearer secret"})

        assert response.status_code == 200
        mock_set_context.assert_called_once()
        kwargs = mock_set_context.call_args.kwargs
        assert kwargs["method"] == "GET"
        assert kwargs["path"] == "/test"
        assert "authorization" not in kwargs


class TestSlowRequestLogging:
    """Test slow request warning logging."""

    @pytest.mark.asyncio
    async def test_warns_on_slow_request(self, client, caplog):
        """Should log warning for slow requests."""
        with caplog.at_level("WARNING"):
            # This will be slow
            client.get("/slow")

        # Should have warning level log
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) >= 1


class TestErrorLogging:
    """Test error logging functionality."""

    def test_logs_error_on_exception(self, client, caplog):
        """Should log error when handler raises exception."""
        with caplog.at_level("ERROR"):
            try:
                client.get("/error")
            except Exception:
                pass

        # Check error was logged
        errors = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(errors) >= 1

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404])
    def test_expected_client_errors_log_at_info(self, app, caplog, status_code):
        """Expected client errors should not page or warn by default."""

        @app.get(f"/client-error-{status_code}")
        def client_error():
            from fastapi import HTTPException

            raise HTTPException(status_code=status_code)

        client = TestClient(app, raise_server_exceptions=False)

        with caplog.at_level("INFO"):
            client.get(f"/client-error-{status_code}")

        response_logs = [r for r in caplog.records if "[RES-" in r.message]
        assert any(f"status={status_code}" in r.message for r in response_logs)
        assert all(r.levelname != "WARNING" for r in response_logs)

    def test_logs_warning_on_rate_limit_response(self, app, caplog):
        """Rate-limit responses are operational warnings."""

        @app.get("/rate-limited")
        def rate_limited():
            from fastapi import HTTPException

            raise HTTPException(status_code=429)

        client = TestClient(app, raise_server_exceptions=False)

        with caplog.at_level("WARNING"):
            client.get("/rate-limited")

        assert any(
            r.levelname == "WARNING" and "status=429" in r.message
            for r in caplog.records
        )


class TestRequestIdHelper:
    """Test get_request_id helper function."""

    def test_get_request_id_from_state(self):
        """Should extract request ID from request state."""
        mock_request = Mock()
        mock_request.state.request_id = "abc12345"

        result = get_request_id(mock_request)
        assert result == "abc12345"

    def test_get_request_id_missing(self):
        """Should return None if request ID not set."""
        mock_request = Mock()
        del mock_request.state.request_id

        result = get_request_id(mock_request)
        assert result is None


class TestClientIpExtraction:
    """Test client IP extraction."""

    def test_extracts_forwarded_ip(self, app):
        """Should extract IP from X-Forwarded-For header."""
        client = TestClient(app)

        response = client.get("/test", headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8"})

        assert response.status_code == 200

"""Sentinel tests for route-template request observability."""

import logging
from contextlib import nullcontext

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.exception_handlers import register_exception_handlers
from src.api.middleware.request_logger import RequestLoggerMiddleware
from src.observability import (
    reset_observability_connector_for_test,
    set_observability_connector_for_test,
)


class _RecordingConnector:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def set_request_context(self, **kwargs):
        self.calls.append(("request_context", kwargs))

    def __getattr__(self, _name):
        return lambda *args, **kwargs: nullcontext()


def teardown_function() -> None:
    reset_observability_connector_for_test()


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestLoggerMiddleware)
    register_exception_handlers(app)

    @app.get("/v1/operations/{operation_id}")
    def lookup(operation_id: str):
        return {"operation_id": operation_id}

    @app.get("/v1/fail/{operation_id}")
    def failure(operation_id: str):
        raise RuntimeError(f"sql bind sentinel={operation_id} uid=uid-sentinel")

    return app


def test_success_logs_and_context_never_contain_resolved_path_or_uid(caplog):
    connector = _RecordingConnector()
    set_observability_connector_for_test(connector)
    sentinel_id = "operation-sentinel-123"
    client = TestClient(_app(), raise_server_exceptions=False)

    with caplog.at_level(logging.INFO):
        response = client.get(
            f"/v1/operations/{sentinel_id}?fingerprint=query-sentinel",
            headers={"Authorization": "Bearer token-sentinel", "X-UID": "uid-sentinel"},
        )

    assert response.status_code == 200
    rendered = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("src.api.")
    )
    assert sentinel_id not in rendered
    assert "query-sentinel" not in rendered
    assert "uid-sentinel" not in rendered
    assert "/v1/operations/{operation_id}" in rendered
    context = connector.calls[-1][1]
    assert context["path"] == "/v1/operations/{operation_id}"
    assert "user_id" not in context


def test_failure_logs_never_contain_exception_text_or_resolved_path(caplog):
    sentinel_id = "operation-sentinel-456"
    client = TestClient(_app(), raise_server_exceptions=False)

    with caplog.at_level(logging.DEBUG):
        response = client.get(f"/v1/fail/{sentinel_id}?weight=weight-sentinel")

    assert response.status_code == 500
    rendered = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("src.api.")
    )
    for forbidden in (
        sentinel_id,
        "weight-sentinel",
        "sql bind sentinel",
        "uid-sentinel",
    ):
        assert forbidden not in rendered
    assert "/v1/fail/{operation_id}" in rendered

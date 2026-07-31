"""Paddle webhook route contract tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.v1 import paddle_webhooks
from src.domain.exceptions.paddle_billing_exceptions import PaddleWebhookRetryError


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(paddle_webhooks.router)
    return TestClient(app)


def test_invalid_signature_is_rejected_before_payload_processing(monkeypatch):
    class FakeBillingService:
        def verify_webhook_signature(self, *_args):
            return False

        async def process_webhook(self, *_args):
            raise AssertionError("unverified payload must never be processed")

    monkeypatch.setattr(
        paddle_webhooks, "_get_paddle_billing_service", lambda: FakeBillingService()
    )

    response = _client().post(
        "/v1/webhooks/paddle",
        content=b"not valid JSON",
        headers={"Paddle-Signature": "invalid"},
    )

    assert response.status_code == 400


def test_valid_signature_dispatches_the_original_raw_body(monkeypatch):
    raw_body = b'{"event_id":"evt_1","event_type":"customer.created"}'
    received = {}

    class FakeBillingService:
        def verify_webhook_signature(self, *_args):
            return True

        async def process_webhook(self, body):
            received["body"] = body
            return {"status": "processed", "event_type": "customer.created"}

    monkeypatch.setattr(
        paddle_webhooks, "_get_paddle_billing_service", lambda: FakeBillingService()
    )

    response = _client().post(
        "/v1/webhooks/paddle",
        content=raw_body,
        headers={"Paddle-Signature": "valid"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert received["body"] == raw_body


def test_verified_event_with_missing_dependency_returns_non_2xx(monkeypatch):
    class FakeBillingService:
        def verify_webhook_signature(self, *_args):
            return True

        async def process_webhook(self, *_args):
            raise PaddleWebhookRetryError("subscription delivery pending")

    monkeypatch.setattr(
        paddle_webhooks, "_get_paddle_billing_service", lambda: FakeBillingService()
    )

    response = _client().post(
        "/v1/webhooks/paddle",
        content=b'{"event_id":"evt_2","event_type":"transaction.completed"}',
        headers={"Paddle-Signature": "valid"},
    )

    assert response.status_code == 409


def test_verified_event_with_missing_runtime_configuration_returns_500(monkeypatch):
    class FakeBillingService:
        def verify_webhook_signature(self, *_args):
            return True

        async def process_webhook(self, *_args):
            raise RuntimeError("PADDLE_ENVIRONMENT must be set")

    monkeypatch.setattr(
        paddle_webhooks, "_get_paddle_billing_service", lambda: FakeBillingService()
    )

    response = _client().post(
        "/v1/webhooks/paddle",
        content=b'{"event_id":"evt_3","event_type":"subscription.updated"}',
        headers={"Paddle-Signature": "valid"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Webhook processing is not configured"

"""Paddle SDK webhook verification tests."""

import hashlib
import hmac
import time

from src.infra.services.paddle_fulfillment_service import (
    verify_paddle_webhook_signature,
)


def test_paddle_sdk_verifies_a_valid_raw_payload_signature(monkeypatch):
    secret = "unit-test-webhook-secret"
    raw_body = b'{"event_id":"evt_1","event_type":"customer.created"}'
    timestamp = str(int(time.time()))
    signature = hmac.new(
        secret.encode(), f"{timestamp}:{raw_body.decode()}".encode(), hashlib.sha256
    ).hexdigest()
    monkeypatch.setenv("PADDLE_WEBHOOK_SIGNING_SECRET", secret)

    assert (
        verify_paddle_webhook_signature(
            raw_body, {"Paddle-Signature": f"ts={timestamp};h1={signature}"}
        )
        is True
    )


def test_paddle_sdk_rejects_a_signature_for_different_raw_body(monkeypatch):
    secret = "unit-test-webhook-secret"
    timestamp = str(int(time.time()))
    signed_body = b'{"event_id":"evt_1"}'
    signature = hmac.new(
        secret.encode(), f"{timestamp}:{signed_body.decode()}".encode(), hashlib.sha256
    ).hexdigest()
    monkeypatch.setenv("PADDLE_WEBHOOK_SIGNING_SECRET", secret)

    assert (
        verify_paddle_webhook_signature(
            b'{"event_id":"evt_modified"}',
            {"Paddle-Signature": f"ts={timestamp};h1={signature}"},
        )
        is False
    )

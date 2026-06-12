"""Cross-service HMAC contract test for affiliate request signing.

Verifies MealTrack's _sign_request produces the same digest as the
TypeScript createSignature function in nutree-affiliate/api/_lib/signature.ts.
Both sides must use: HMAC-SHA256(secret, f"{timestamp}.{raw_body}")

Known vector computed offline and embedded here so either side can break
independently if the algorithm drifts.
"""
import hashlib
import hmac

from src.infra.adapters.affiliate_service_adapter import _sign_request

# Shared contract vector — also hardcoded in nutree-affiliate signature.test.ts
_SECRET = "test-secret-key"
_TIMESTAMP = "1749600000"
_BODY = (
    '{"event_id":"test-evt-001",'
    '"event_type":"subscription_initial_purchase",'
    '"mealtrack_user_id":"user-123"}'
)
_EXPECTED_DIGEST = "0c1627287a582db38fbb7add6d4d1de535b38404f71ac2b8f695a31276e60fd6"


def test_sign_request_matches_known_vector():
    """Python signing matches the offline-computed cross-service contract vector."""
    result = _sign_request(_BODY, _TIMESTAMP, _SECRET)
    assert result == _EXPECTED_DIGEST


def test_sign_request_algorithm_is_hmac_sha256_of_timestamp_dot_body():
    """Algorithm is exactly HMAC-SHA256(secret, '{timestamp}.{body}')."""
    message = f"{_TIMESTAMP}.{_BODY}"
    expected = hmac.new(_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    assert _sign_request(_BODY, _TIMESTAMP, _SECRET) == expected


def test_different_secret_produces_different_digest():
    sig1 = _sign_request(_BODY, _TIMESTAMP, "secret-a")
    sig2 = _sign_request(_BODY, _TIMESTAMP, "secret-b")
    assert sig1 != sig2


def test_different_timestamp_produces_different_digest():
    sig1 = _sign_request(_BODY, "1749600000", _SECRET)
    sig2 = _sign_request(_BODY, "1749600001", _SECRET)
    assert sig1 != sig2


def test_different_body_produces_different_digest():
    body2 = _BODY.replace("user-123", "user-456")
    assert _sign_request(_BODY, _TIMESTAMP, _SECRET) != _sign_request(body2, _TIMESTAMP, _SECRET)

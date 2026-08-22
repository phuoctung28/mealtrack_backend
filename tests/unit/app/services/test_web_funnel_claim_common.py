from datetime import timedelta

from src.app.services.web_funnel_claim_common import (
    hash_secret,
    is_active_standard,
    token_matches,
    utcnow,
)


def test_claim_secret_comparison_never_requires_plaintext_storage() -> None:
    assert token_matches("a" * 48, hash_secret("a" * 48))
    assert not token_matches("b" * 48, hash_secret("a" * 48))


def test_standard_entitlement_requires_unexpired_authoritative_value() -> None:
    active = {"subscriber": {"entitlements": {"standard": {"expires_date": (utcnow() + timedelta(hours=1)).isoformat()}}}}
    expired = {"subscriber": {"entitlements": {"standard": {"expires_date": (utcnow() - timedelta(hours=1)).isoformat()}}}}
    assert is_active_standard(active)
    assert not is_active_standard(expired)
    assert not is_active_standard({"subscriber": {"entitlements": {}}})

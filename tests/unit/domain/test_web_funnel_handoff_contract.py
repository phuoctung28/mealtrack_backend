import pytest

from src.domain.model.web_funnel_handoff import (
    LeadState,
    hash_lead_access_key,
    mask_claim_email,
    normalize_claim_email,
    verify_lead_access_key,
)


def test_paid_lead_never_returns_to_draft() -> None:
    assert not LeadState.PAYMENT_VERIFIED.can_transition_to(LeadState.DRAFT)
    assert LeadState.PAYMENT_VERIFIED.can_transition_to(LeadState.CLAIM_EMAIL_SENT)


def test_claimed_lead_is_terminal() -> None:
    assert not LeadState.CLAIMED.can_transition_to(LeadState.CLAIM_REVOKED)
    assert LeadState.CLAIMED.can_transition_to(LeadState.CLAIMED)


def test_normalize_claim_email_uses_nfc_casefold_and_idna() -> None:
    assert normalize_claim_email("  T\u00c9ST@B\u00dcCHER.example ") == "t\u00e9st@xn--bcher-kva.example"


@pytest.mark.parametrize(
    "email",
    [
        "missing-at",
        "a@",
        "\x00a@example.com",
        "a@example.com@attacker.test",
        "a b@example.com",
        "a@exam ple.com",
        ".a@example.com",
    ],
)
def test_normalize_claim_email_rejects_invalid_values(email: str) -> None:
    with pytest.raises(ValueError):
        normalize_claim_email(email)


def test_lead_access_key_is_hash_only_and_constant_time_verified() -> None:
    digest = hash_lead_access_key("browser-capability")
    assert digest != "browser-capability"
    assert verify_lead_access_key("browser-capability", digest)
    assert not verify_lead_access_key("other-capability", digest)


def test_mask_claim_email_does_not_return_full_local_part() -> None:
    assert mask_claim_email("person@example.com") == "pe***@example.com"

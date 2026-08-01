"""Stable, provider-neutral contracts for the web-to-app handoff."""

from __future__ import annotations

import hashlib
import hmac
import unicodedata
from enum import StrEnum


class LeadState(StrEnum):
    """Durable lifecycle states for an email-first web lead."""

    DRAFT = "draft"
    CHECKOUT_STARTED = "checkout_started"
    PAYMENT_VERIFIED = "payment_verified"
    CLAIM_EMAIL_SENT = "claim_email_sent"
    CLAIMED = "claimed"
    EMAIL_DELIVERY_DELAYED = "email_delivery_delayed"
    CLAIM_EXPIRED = "claim_expired"
    CLAIM_REVOKED = "claim_revoked"
    CLAIM_CONFLICT = "claim_conflict"

    def can_transition_to(self, target: LeadState) -> bool:
        """Return whether a state transition preserves paid-claim history."""
        if self is target:
            return True
        return target in _ALLOWED_TRANSITIONS[self]


_ALLOWED_TRANSITIONS: dict[LeadState, set[LeadState]] = {
    LeadState.DRAFT: {LeadState.CHECKOUT_STARTED},
    LeadState.CHECKOUT_STARTED: {LeadState.PAYMENT_VERIFIED},
    LeadState.PAYMENT_VERIFIED: {
        LeadState.CLAIM_EMAIL_SENT,
        LeadState.EMAIL_DELIVERY_DELAYED,
        LeadState.CLAIM_REVOKED,
    },
    LeadState.CLAIM_EMAIL_SENT: {
        LeadState.CLAIMED,
        LeadState.EMAIL_DELIVERY_DELAYED,
        LeadState.CLAIM_EXPIRED,
        LeadState.CLAIM_REVOKED,
        LeadState.CLAIM_CONFLICT,
    },
    LeadState.EMAIL_DELIVERY_DELAYED: {
        LeadState.CLAIM_EMAIL_SENT,
        LeadState.CLAIM_REVOKED,
    },
    LeadState.CLAIM_EXPIRED: {LeadState.CLAIM_EMAIL_SENT, LeadState.CLAIM_REVOKED},
    LeadState.CLAIMED: set(),
    LeadState.CLAIM_REVOKED: set(),
    LeadState.CLAIM_CONFLICT: set(),
}


def normalize_claim_email(value: str) -> str:
    """Normalize an email without provider-specific alias rewriting."""
    candidate = unicodedata.normalize("NFC", value).strip()
    if candidate.count("@") != 1:
        raise ValueError("Email must contain exactly one local part and domain")
    if any(
        character.isspace() or ord(character) < 32 or ord(character) == 127
        for character in candidate
    ):
        raise ValueError("Email contains a control character")
    local, separator, domain = candidate.partition("@")
    if not separator or not local or not domain:
        raise ValueError("Email must contain a local part and domain")
    if len(candidate) > 254 or len(local) > 64:
        raise ValueError("Email is too long")
    if local.startswith(".") or local.endswith(".") or ".." in local:
        raise ValueError("Email local part is invalid")
    try:
        canonical_domain = domain.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("Email domain is invalid") from exc
    return f"{local.casefold()}@{canonical_domain.casefold()}"


def hash_lead_access_key(value: str) -> str:
    """Hash a browser capability before persistence."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify_lead_access_key(value: str, expected_hash: str) -> bool:
    """Compare a browser capability with its persisted digest in constant time."""
    return hmac.compare_digest(hash_lead_access_key(value), expected_hash)


def mask_claim_email(value: str) -> str:
    """Return a stable, low-disclosure email projection for browser responses."""
    local, _, domain = normalize_claim_email(value).partition("@")
    visible = local[:2] if len(local) > 1 else local
    return f"{visible}***@{domain}"

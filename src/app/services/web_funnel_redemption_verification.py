"""Fail-closed normalization of server-fetched RevenueCat customer facts."""

from dataclasses import dataclass
from enum import StrEnum

from src.app.services.web_funnel_claim_common import is_active_standard


class RevenueCatVerificationState(StrEnum):
    VERIFIED = "verified"
    NOT_BOUND = "not_bound"
    NOT_ENTITLED = "not_entitled"


@dataclass(frozen=True)
class RevenueCatVerification:
    """Safe provider facts used by correlation and finalization only."""

    state: RevenueCatVerificationState
    product_id: str | None = None


def _verify(
    subscriber: dict | None,
    *,
    original_app_user_id: str,
    allowed_product_ids: set[str],
) -> RevenueCatVerification:
    customer = (subscriber or {}).get("subscriber")
    if (
        not isinstance(customer, dict)
        or customer.get("original_app_user_id") != original_app_user_id
    ):
        return RevenueCatVerification(RevenueCatVerificationState.NOT_BOUND)
    entitlement = customer.get("entitlements", {}).get("standard")
    product_id = (
        entitlement.get("product_identifier") if isinstance(entitlement, dict) else None
    )
    if (
        not isinstance(product_id, str)
        or product_id not in allowed_product_ids
        or not is_active_standard(subscriber)
    ):
        return RevenueCatVerification(RevenueCatVerificationState.NOT_ENTITLED)
    return RevenueCatVerification(RevenueCatVerificationState.VERIFIED, product_id)


def verify_bound_web_customer(
    subscriber: dict | None,
    *,
    original_app_user_id: str,
    allowed_product_ids: set[str],
) -> RevenueCatVerification:
    """Verify the browser hint names the authoritative anonymous customer."""
    return _verify(
        subscriber,
        original_app_user_id=original_app_user_id,
        allowed_product_ids=allowed_product_ids,
    )


def verify_redeemed_customer(
    subscriber: dict | None,
    *,
    original_app_user_id: str,
    allowed_product_ids: set[str],
) -> RevenueCatVerification:
    """Verify a Firebase UID resolves to the previously bound web customer."""
    return _verify(
        subscriber,
        original_app_user_id=original_app_user_id,
        allowed_product_ids=allowed_product_ids,
    )

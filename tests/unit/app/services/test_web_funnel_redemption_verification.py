"""Provider facts for anonymous web-purchase redemption are fail-closed."""

from src.app.services.web_funnel_redemption_verification import (
    RevenueCatVerificationState,
    verify_bound_web_customer,
    verify_redeemed_customer,
)


def _subscriber(*, original: str, product: str = "web_monthly", active: bool = True):
    return {
        "subscriber": {
            "original_app_user_id": original,
            "entitlements": {
                "standard": {
                    "expires_date": None if active else "2020-01-01T00:00:00Z",
                    "product_identifier": product,
                }
            },
        }
    }


def test_bound_customer_requires_its_own_original_id_and_allowed_product():
    result = verify_bound_web_customer(
        _subscriber(original="$RCAnonymousID:web"),
        original_app_user_id="$RCAnonymousID:web",
        allowed_product_ids={"web_monthly"},
    )

    assert result.state is RevenueCatVerificationState.VERIFIED


def test_redeemed_customer_requires_the_bound_original_customer_id():
    result = verify_redeemed_customer(
        _subscriber(original="$RCAnonymousID:web"),
        original_app_user_id="$RCAnonymousID:web",
        allowed_product_ids={"web_monthly"},
    )

    assert result.state is RevenueCatVerificationState.VERIFIED


def test_different_original_customer_cannot_finalize_even_when_entitled():
    result = verify_redeemed_customer(
        _subscriber(original="$RCAnonymousID:other"),
        original_app_user_id="$RCAnonymousID:web",
        allowed_product_ids={"web_monthly"},
    )

    assert result.state is RevenueCatVerificationState.NOT_BOUND


def test_missing_or_disallowed_product_fails_closed():
    result = verify_bound_web_customer(
        _subscriber(original="$RCAnonymousID:web", product="native_monthly"),
        original_app_user_id="$RCAnonymousID:web",
        allowed_product_ids={"web_monthly"},
    )

    assert result.state is RevenueCatVerificationState.NOT_ENTITLED

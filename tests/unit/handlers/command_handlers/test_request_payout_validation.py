import pytest

from src.app.handlers.command_handlers.referral.request_payout_handler import (
    validate_payout_payment_details,
)


def test_validate_payout_accepts_momo_phone() -> None:
    validate_payout_payment_details(
        "momo",
        {"phone": "0900000000", "country": "VN", "currency": "VND"},
    )


def test_validate_payout_accepts_bank_account() -> None:
    validate_payout_payment_details(
        "bank",
        {"bank": "VCB", "account": "123456789", "country": "VN", "currency": "VND"},
    )


@pytest.mark.parametrize(
    ("method", "details", "error"),
    [
        ("paypal", {"account": "x"}, "invalid_payment_method"),
        ("momo", {}, "missing_momo_phone"),
        ("bank", {"account": "123"}, "missing_bank_name"),
        ("bank", {"bank": "VCB"}, "missing_bank_account"),
        ("momo", {"phone": "090", "country": "VNM"}, "invalid_payment_country"),
        ("momo", {"phone": "090", "currency": "VNDD"}, "invalid_payment_currency"),
    ],
)
def test_validate_payout_rejects_invalid_details(
    method: str,
    details: dict,
    error: str,
) -> None:
    with pytest.raises(ValueError, match=error):
        validate_payout_payment_details(method, details)

# tests/unit/handlers/test_validate_code_handler.py
"""Unit tests for ValidateCodeQueryHandler — unified promo + referral validation."""
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app.queries.codes.validate_code_query import (
    CodeValidationError,
    ValidateCodeQuery,
)
from src.infra.database.models.promo_code import PromoCode, PromoCodeRedemption
from src.infra.database.models.referral.referral_code import ReferralCode
from src.infra.database.models.referral.referral_conversion import ReferralConversion

# ── Factories ────────────────────────────────────────────────────────────────

def _make_promo(
    code="SUMMER30",
    is_active=True,
    expires_at=None,
    max_uses=100,
    current_uses=0,
    rc_offering_id="summer_sale_2024",
    description="30% off annual plan",
):
    p = PromoCode()
    p.id = "promo-id-1"
    p.code = code
    p.is_active = is_active
    p.expires_at = expires_at
    p.max_uses = max_uses
    p.current_uses = current_uses
    p.rc_offering_id = rc_offering_id
    p.description = description
    return p


def _make_referral_code(code="ALEX123", user_id="referrer-id"):
    r = ReferralCode()
    r.code = code
    r.user_id = user_id
    return r


def _mock_uow(promo=None, promo_redemption=None, referral=None, conversion=None, referrer_row=None):
    """Build a mock AsyncUnitOfWork plus two repo mocks."""
    mock_uow = MagicMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)

    # Session mock for the referrer-name query
    if referrer_row is not None:
        mock_result = MagicMock()
        mock_result.first.return_value = referrer_row
    else:
        mock_result = MagicMock()
        mock_result.first.return_value = None
    mock_uow.session = MagicMock()
    mock_uow.session.execute = AsyncMock(return_value=mock_result)

    mock_promo_repo = AsyncMock()
    mock_promo_repo.get_by_code = AsyncMock(return_value=promo)
    mock_promo_repo.get_redemption = AsyncMock(return_value=promo_redemption)

    mock_referral_repo = AsyncMock()
    mock_referral_repo.get_code_by_code = AsyncMock(return_value=referral)
    mock_referral_repo.get_conversion_by_referred_user = AsyncMock(return_value=conversion)
    mock_uow.promo_codes = mock_promo_repo
    mock_uow.referrals = mock_referral_repo

    return mock_uow, mock_promo_repo, mock_referral_repo


HANDLER_PATH = "src.app.handlers.query_handlers.codes.validate_code_handler"


@contextmanager
def _patch(mock_uow, mock_promo_repo, mock_referral_repo):
    assert mock_uow.promo_codes is mock_promo_repo
    assert mock_uow.referrals is mock_referral_repo
    with patch(f"{HANDLER_PATH}.AsyncUnitOfWork", return_value=mock_uow):
        yield


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_valid_promo_code_returns_promo_type():
    promo = _make_promo()
    mock_uow, mock_promo_repo, mock_referral_repo = _mock_uow(promo=promo)

    with _patch(mock_uow, mock_promo_repo, mock_referral_repo):
        from src.app.handlers.query_handlers.codes.validate_code_handler import (
            ValidateCodeQueryHandler,
        )
        result = await ValidateCodeQueryHandler().handle(
            ValidateCodeQuery(code="SUMMER30", user_id="user-abc")
        )

    assert result["type"] == "promo_code"
    assert result["code"] == "SUMMER30"
    assert result["is_valid"] is True
    assert result["rc_offering_id"] == "summer_sale_2024"
    assert result["description"] == "30% off annual plan"


@pytest.mark.asyncio
async def test_valid_referral_code_returns_referral_type():
    referral = _make_referral_code(user_id="referrer-id")
    row = MagicMock()
    row.first_name = "Alex"
    row.display_name = None
    mock_uow, mock_promo_repo, mock_referral_repo = _mock_uow(referral=referral, referrer_row=row)

    with _patch(mock_uow, mock_promo_repo, mock_referral_repo):
        from src.app.handlers.query_handlers.codes.validate_code_handler import (
            ValidateCodeQueryHandler,
        )
        result = await ValidateCodeQueryHandler().handle(
            ValidateCodeQuery(code="ALEX123", user_id="user-456")
        )

    assert result["type"] == "referral_code"
    assert result["code"] == "ALEX123"
    assert result["is_valid"] is True
    assert result["referrer_name"] == "Alex"
    assert result["discount_monthly"] == 199000
    assert result["discount_annual"] == 499000
    # Mobile reads commission_rewards to render localized reward strings;
    # an empty dict here silently falls back to mobile's hardcoded defaults.
    assert result["commission_rewards"], "commission_rewards must be exposed for mobile"


@pytest.mark.asyncio
async def test_unknown_code_raises_404():
    mock_uow, mock_promo_repo, mock_referral_repo = _mock_uow(promo=None, referral=None)

    with _patch(mock_uow, mock_promo_repo, mock_referral_repo), \
         patch(f"{HANDLER_PATH}.AffiliateServiceAdapter") as MockAdapter:
        MockAdapter.return_value.validate_code = AsyncMock(
            return_value=MagicMock(active=False)
        )
        from src.app.handlers.query_handlers.codes.validate_code_handler import (
            ValidateCodeQueryHandler,
        )
        with pytest.raises(CodeValidationError) as exc_info:
            await ValidateCodeQueryHandler().handle(
                ValidateCodeQuery(code="DOESNOTEXIST", user_id="user-abc")
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Code not found"


@pytest.mark.asyncio
async def test_own_referral_code_raises_422():
    referral = _make_referral_code(user_id="same-user")
    mock_uow, mock_promo_repo, mock_referral_repo = _mock_uow(referral=referral)

    with _patch(mock_uow, mock_promo_repo, mock_referral_repo):
        from src.app.handlers.query_handlers.codes.validate_code_handler import (
            ValidateCodeQueryHandler,
        )
        with pytest.raises(CodeValidationError) as exc_info:
            await ValidateCodeQueryHandler().handle(
                ValidateCodeQuery(code="ALEX123", user_id="same-user")
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "You cannot use your own referral code"


@pytest.mark.asyncio
async def test_expired_promo_raises_422():
    past = datetime.now(UTC) - timedelta(days=1)
    promo = _make_promo(expires_at=past)
    mock_uow, mock_promo_repo, mock_referral_repo = _mock_uow(promo=promo)

    with _patch(mock_uow, mock_promo_repo, mock_referral_repo):
        from src.app.handlers.query_handlers.codes.validate_code_handler import (
            ValidateCodeQueryHandler,
        )
        with pytest.raises(CodeValidationError) as exc_info:
            await ValidateCodeQueryHandler().handle(
                ValidateCodeQuery(code="SUMMER30", user_id="user-abc")
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "This code has expired"


@pytest.mark.asyncio
async def test_exhausted_promo_raises_422():
    promo = _make_promo(max_uses=10, current_uses=10)
    mock_uow, mock_promo_repo, mock_referral_repo = _mock_uow(promo=promo)

    with _patch(mock_uow, mock_promo_repo, mock_referral_repo):
        from src.app.handlers.query_handlers.codes.validate_code_handler import (
            ValidateCodeQueryHandler,
        )
        with pytest.raises(CodeValidationError) as exc_info:
            await ValidateCodeQueryHandler().handle(
                ValidateCodeQuery(code="SUMMER30", user_id="user-abc")
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Code is no longer available"


@pytest.mark.asyncio
async def test_already_redeemed_promo_raises_422():
    promo = _make_promo()
    redemption = PromoCodeRedemption()
    mock_uow, mock_promo_repo, mock_referral_repo = _mock_uow(promo=promo, promo_redemption=redemption)

    with _patch(mock_uow, mock_promo_repo, mock_referral_repo):
        from src.app.handlers.query_handlers.codes.validate_code_handler import (
            ValidateCodeQueryHandler,
        )
        with pytest.raises(CodeValidationError) as exc_info:
            await ValidateCodeQueryHandler().handle(
                ValidateCodeQuery(code="SUMMER30", user_id="user-abc")
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "You have already used this code"


@pytest.mark.asyncio
async def test_already_referred_user_raises_422():
    referral = _make_referral_code(user_id="referrer-id")
    conversion = ReferralConversion()
    mock_uow, mock_promo_repo, mock_referral_repo = _mock_uow(
        referral=referral, conversion=conversion
    )

    with _patch(mock_uow, mock_promo_repo, mock_referral_repo):
        from src.app.handlers.query_handlers.codes.validate_code_handler import (
            ValidateCodeQueryHandler,
        )
        with pytest.raises(CodeValidationError) as exc_info:
            await ValidateCodeQueryHandler().handle(
                ValidateCodeQuery(code="ALEX123", user_id="user-456")
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "You have already used this code"


@pytest.mark.asyncio
async def test_inactive_promo_raises_422():
    promo = _make_promo(is_active=False)
    mock_uow, mock_promo_repo, mock_referral_repo = _mock_uow(promo=promo)

    with _patch(mock_uow, mock_promo_repo, mock_referral_repo):
        from src.app.handlers.query_handlers.codes.validate_code_handler import (
            ValidateCodeQueryHandler,
        )
        with pytest.raises(CodeValidationError) as exc_info:
            await ValidateCodeQueryHandler().handle(
                ValidateCodeQuery(code="SUMMER30", user_id="user-abc")
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Code is no longer available"


@pytest.mark.asyncio
async def test_referral_falls_back_to_display_name():
    referral = _make_referral_code(user_id="referrer-id")
    row = MagicMock()
    row.first_name = None
    row.display_name = "Alex Smith"
    mock_uow, mock_promo_repo, mock_referral_repo = _mock_uow(referral=referral, referrer_row=row)

    with _patch(mock_uow, mock_promo_repo, mock_referral_repo):
        from src.app.handlers.query_handlers.codes.validate_code_handler import (
            ValidateCodeQueryHandler,
        )
        result = await ValidateCodeQueryHandler().handle(
            ValidateCodeQuery(code="ALEX123", user_id="user-456")
        )

    assert result["referrer_name"] == "Alex"


@pytest.mark.asyncio
async def test_referral_falls_back_to_friend_when_no_name():
    referral = _make_referral_code(user_id="referrer-id")
    mock_uow, mock_promo_repo, mock_referral_repo = _mock_uow(referral=referral, referrer_row=None)

    with _patch(mock_uow, mock_promo_repo, mock_referral_repo):
        from src.app.handlers.query_handlers.codes.validate_code_handler import (
            ValidateCodeQueryHandler,
        )
        result = await ValidateCodeQueryHandler().handle(
            ValidateCodeQuery(code="ALEX123", user_id="user-456")
        )

    assert result["referrer_name"] == "Friend"


@pytest.mark.asyncio
async def test_commission_rewards_match_runtime_settings():
    """Commission rewards in the response must match the live settings instance.

    Render redeploy -> settings re-load -> response reflects the new value.
    """
    referral = _make_referral_code(user_id="referrer-id")
    row = MagicMock()
    row.first_name = "Alex"
    row.display_name = None
    mock_uow, mock_promo_repo, mock_referral_repo = _mock_uow(referral=referral, referrer_row=row)

    overridden = {"USD": 5, "VND": 100000, "EUR": 4.5, "default": 5}
    with _patch(mock_uow, mock_promo_repo, mock_referral_repo), \
         patch(f"{HANDLER_PATH}.settings") as mock_settings:
        mock_settings.REFERRAL_COMMISSIONS = overridden
        from src.app.handlers.query_handlers.codes.validate_code_handler import (
            ValidateCodeQueryHandler,
        )
        result = await ValidateCodeQueryHandler().handle(
            ValidateCodeQuery(code="ALEX123", user_id="user-456")
        )

    assert result["commission_rewards"] == overridden

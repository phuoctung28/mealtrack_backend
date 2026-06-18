"""Unit tests for affiliate code fallback in ValidateCodeQueryHandler.

MealTrack stores no attribution state — nutree-affiliate owns dedup.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app.handlers.query_handlers.codes.validate_code_handler import (
    ValidateCodeQueryHandler,
)
from src.app.queries.codes.validate_code_query import (
    CodeValidationError,
    ValidateCodeQuery,
)
from src.domain.ports.affiliate_service_port import AffiliateCodeValidationResult

MODULE = "src.app.handlers.query_handlers.codes.validate_code_handler"
QUERY = ValidateCodeQuery(code="AFFCODE1", user_id="user-1")


def _make_uow(*, promo=None, ref_code=None, ref_existing=None):
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.promo_codes.get_by_code = AsyncMock(return_value=promo)
    uow.promo_codes.get_redemption = AsyncMock(return_value=None)
    uow.referrals.get_code_by_code = AsyncMock(return_value=ref_code)
    uow.referrals.get_conversion_by_referred_user = AsyncMock(return_value=ref_existing)
    uow.session.execute = AsyncMock(
        return_value=MagicMock(first=MagicMock(return_value=None))
    )
    return uow


@pytest.mark.asyncio
async def test_promo_code_wins_before_affiliate():
    """Promo match returns promo_code type without calling affiliate service."""
    promo = MagicMock()
    promo.is_active = True
    promo.expires_at = None
    promo.current_uses = 0
    promo.max_uses = 100
    promo.code = "AFFCODE1"
    promo.rc_offering_id = None
    promo.description = None

    mock_uow = _make_uow(promo=promo)
    with (
        patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_svc_cls,
    ):
        result = await ValidateCodeQueryHandler().handle(QUERY)

    assert result["type"] == "promo_code"
    mock_svc_cls.assert_not_called()


@pytest.mark.asyncio
async def test_referral_code_wins_before_affiliate():
    """Referral code match returns referral_code type without calling affiliate service."""
    ref = MagicMock()
    ref.user_id = "other-user"
    ref.code = "AFFCODE1"

    mock_uow = _make_uow(ref_code=ref)
    with (
        patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_svc_cls,
        patch(f"{MODULE}.settings") as mock_settings,
    ):
        mock_settings.AFFILIATE_INTEGRATION_ENABLED = True
        mock_settings.REFERRAL_COMMISSIONS = {"VND": 50000, "default": 2}
        result = await ValidateCodeQueryHandler().handle(QUERY)

    assert result["type"] == "referral_code"
    mock_svc_cls.assert_not_called()


@pytest.mark.asyncio
async def test_affiliate_code_returned_when_integration_enabled():
    """Affiliate fallback returns affiliate_code; no local attribution stored."""
    mock_uow = _make_uow()
    aff_result = AffiliateCodeValidationResult(
        active=True,
        affiliate_id="aff-1",
        code_id="code-1",
        display_name="Alex",
        partner_type="pt",
    )
    with (
        patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_svc_cls,
        patch(f"{MODULE}.settings") as mock_settings,
    ):
        mock_settings.AFFILIATE_INTEGRATION_ENABLED = True
        mock_svc_cls.return_value.validate_code = AsyncMock(return_value=aff_result)
        result = await ValidateCodeQueryHandler().handle(QUERY)

    assert result["type"] == "affiliate_code"
    assert result["is_valid"] is True
    assert result["affiliate_id"] == "aff-1"
    assert result["display_name"] == "Alex"


@pytest.mark.asyncio
async def test_affiliate_not_called_when_integration_disabled():
    """No affiliate call when the integration gate is off."""
    mock_uow = _make_uow()
    with (
        patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_svc_cls,
        patch(f"{MODULE}.settings") as mock_settings,
    ):
        mock_settings.AFFILIATE_INTEGRATION_ENABLED = False
        with pytest.raises(CodeValidationError) as exc_info:
            await ValidateCodeQueryHandler().handle(QUERY)

    assert exc_info.value.status_code == 404
    mock_svc_cls.assert_not_called()


@pytest.mark.asyncio
async def test_inactive_affiliate_code_raises_404():
    """Affiliate returns active=False → 404 (no local state needed)."""
    mock_uow = _make_uow()
    with (
        patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_svc_cls,
        patch(f"{MODULE}.settings") as mock_settings,
    ):
        mock_settings.AFFILIATE_INTEGRATION_ENABLED = True
        mock_svc_cls.return_value.validate_code = AsyncMock(
            return_value=AffiliateCodeValidationResult(active=False)
        )
        with pytest.raises(CodeValidationError) as exc_info:
            await ValidateCodeQueryHandler().handle(QUERY)

    assert exc_info.value.status_code == 404

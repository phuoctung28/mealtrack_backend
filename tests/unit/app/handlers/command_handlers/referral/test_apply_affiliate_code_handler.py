"""Unit tests for affiliate code apply path in ApplyReferralCodeCommandHandler.

MealTrack stores no attribution state — sends event to nutree-affiliate directly.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app.commands.referral.apply_referral_code_command import ApplyReferralCodeCommand
from src.app.handlers.command_handlers.referral.apply_referral_code_handler import (
    ApplyReferralCodeCommandHandler,
)
from src.domain.ports.affiliate_service_port import AffiliateCodeValidationResult

MODULE = "src.app.handlers.command_handlers.referral.apply_referral_code_handler"

CMD = ApplyReferralCodeCommand(
    user_id="user-1", code="AFFCODE1", discount_applied=199000, currency="VND",
)


def _make_uow(*, ref_code=None, ref_existing=None):
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.referrals.get_code_by_code = AsyncMock(return_value=ref_code)
    uow.referrals.get_conversion_by_referred_user = AsyncMock(return_value=ref_existing)
    uow.referrals.create_conversion = AsyncMock(return_value=MagicMock())
    return uow


@pytest.mark.asyncio
async def test_user_referral_path_creates_conversion_unchanged():
    """Existing referral code creates ReferralConversion — regression guard."""
    ref = MagicMock()
    ref.user_id = "referrer-user"
    mock_uow = _make_uow(ref_code=ref)

    with patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow):
        await ApplyReferralCodeCommandHandler().handle(CMD)

    mock_uow.referrals.create_conversion.assert_called_once_with(
        referrer_user_id="referrer-user",
        referred_user_id="user-1",
        code="AFFCODE1",
        discount=199000,
        currency="VND",
    )


@pytest.mark.asyncio
async def test_referral_self_referral_still_raises():
    ref = MagicMock()
    ref.user_id = "user-1"
    mock_uow = _make_uow(ref_code=ref)

    with patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow):
        with pytest.raises(ValueError, match="self_referral"):
            await ApplyReferralCodeCommandHandler().handle(CMD)


@pytest.mark.asyncio
async def test_referral_already_referred_raises():
    ref = MagicMock()
    ref.user_id = "referrer-user"
    mock_uow = _make_uow(ref_code=ref, ref_existing=MagicMock())

    with patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow):
        with pytest.raises(ValueError, match="already_referred"):
            await ApplyReferralCodeCommandHandler().handle(CMD)


@pytest.mark.asyncio
async def test_affiliate_path_sends_event_no_local_state():
    """Affiliate apply sends event to nutree-affiliate; nothing stored in MealTrack."""
    mock_uow = _make_uow()
    aff_result = AffiliateCodeValidationResult(
        active=True, affiliate_id="aff-1", code_id="code-1",
        display_name="Alex", partner_type="pt",
    )

    with (
        patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_svc_cls,
        patch(f"{MODULE}.settings") as mock_settings,
    ):
        mock_settings.AFFILIATE_INTEGRATION_ENABLED = True
        instance = mock_svc_cls.return_value
        instance.validate_code = AsyncMock(return_value=aff_result)
        instance.send_event = AsyncMock(return_value=True)
        await ApplyReferralCodeCommandHandler().handle(CMD)

    instance.send_event.assert_called_once()
    sent_payload = instance.send_event.call_args[0][0]
    assert sent_payload["event_type"] == "affiliate_attribution_created"
    assert sent_payload["mealtrack_user_id"] == "user-1"
    assert sent_payload["affiliate_id"] == "aff-1"
    assert sent_payload["affiliate_code"] == "AFFCODE1"


@pytest.mark.asyncio
async def test_affiliate_send_failure_does_not_raise():
    """If nutree-affiliate delivery fails, apply still succeeds (fire-and-not-fail)."""
    mock_uow = _make_uow()
    aff_result = AffiliateCodeValidationResult(
        active=True, affiliate_id="aff-1", code_id="code-1",
        display_name="Alex", partner_type="pt",
    )

    with (
        patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_svc_cls,
        patch(f"{MODULE}.settings") as mock_settings,
    ):
        mock_settings.AFFILIATE_INTEGRATION_ENABLED = True
        instance = mock_svc_cls.return_value
        instance.validate_code = AsyncMock(return_value=aff_result)
        instance.send_event = AsyncMock(return_value=False)  # delivery failed
        # should not raise
        await ApplyReferralCodeCommandHandler().handle(CMD)


@pytest.mark.asyncio
async def test_invalid_code_with_integration_disabled_raises():
    mock_uow = _make_uow()

    with (
        patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow),
        patch(f"{MODULE}.settings") as mock_settings,
    ):
        mock_settings.AFFILIATE_INTEGRATION_ENABLED = False
        with pytest.raises(ValueError, match="invalid_code"):
            await ApplyReferralCodeCommandHandler().handle(CMD)


@pytest.mark.asyncio
async def test_affiliate_api_inactive_raises_invalid_code():
    """Affiliate validate returns active=False → invalid_code, no event sent."""
    mock_uow = _make_uow()

    with (
        patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_svc_cls,
        patch(f"{MODULE}.settings") as mock_settings,
    ):
        mock_settings.AFFILIATE_INTEGRATION_ENABLED = True
        instance = mock_svc_cls.return_value
        instance.validate_code = AsyncMock(
            return_value=AffiliateCodeValidationResult(active=False)
        )
        instance.send_event = AsyncMock()
        with pytest.raises(ValueError, match="invalid_code"):
            await ApplyReferralCodeCommandHandler().handle(CMD)

    instance.send_event.assert_not_called()

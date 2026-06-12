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
    uow.affiliate_outbox = AsyncMock()
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
async def test_affiliate_path_enqueues_attribution_no_local_state():
    """Affiliate apply enqueues attribution to outbox; nothing stored in MealTrack."""
    mock_uow = _make_uow()
    aff_result = AffiliateCodeValidationResult(
        active=True, affiliate_id="aff-1", code_id="code-1",
        display_name="Alex", partner_type="pt",
    )

    with (
        patch.dict("os.environ", {"AFFILIATE_INTEGRATION_ENABLED": "true"}),
        patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_svc_cls,
    ):
        mock_svc_cls.return_value.validate_code = AsyncMock(return_value=aff_result)
        await ApplyReferralCodeCommandHandler().handle(CMD)

    mock_uow.affiliate_outbox.enqueue.assert_awaited_once()
    call = mock_uow.affiliate_outbox.enqueue.call_args
    assert call[0][0] == "affiliate_attribution_created"
    payload = call[0][1]
    assert payload["mealtrack_user_id"] == "user-1"
    assert payload["affiliate_id"] == "aff-1"
    assert payload["affiliate_code"] == "AFFCODE1"
    assert call[1]["event_id"] == "attribution_user-1_AFFCODE1"


@pytest.mark.asyncio
async def test_affiliate_duplicate_attribution_does_not_raise():
    """Outbox returning None (duplicate event_id) is silently ignored."""
    mock_uow = _make_uow()
    mock_uow.affiliate_outbox.enqueue = AsyncMock(return_value=None)
    aff_result = AffiliateCodeValidationResult(
        active=True, affiliate_id="aff-1", code_id="code-1",
        display_name="Alex", partner_type="pt",
    )

    with (
        patch.dict("os.environ", {"AFFILIATE_INTEGRATION_ENABLED": "true"}),
        patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_svc_cls,
    ):
        mock_svc_cls.return_value.validate_code = AsyncMock(return_value=aff_result)
        await ApplyReferralCodeCommandHandler().handle(CMD)  # must not raise


@pytest.mark.asyncio
async def test_invalid_code_with_integration_disabled_raises():
    mock_uow = _make_uow()

    with (
        patch.dict("os.environ", {"AFFILIATE_INTEGRATION_ENABLED": "false"}),
        patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow),
    ):
        with pytest.raises(ValueError, match="invalid_code"):
            await ApplyReferralCodeCommandHandler().handle(CMD)


@pytest.mark.asyncio
async def test_affiliate_api_inactive_raises_invalid_code():
    """Affiliate validate returns active=False → invalid_code, no event sent."""
    mock_uow = _make_uow()

    with (
        patch.dict("os.environ", {"AFFILIATE_INTEGRATION_ENABLED": "true"}),
        patch(f"{MODULE}.AsyncUnitOfWork", return_value=mock_uow),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_svc_cls,
    ):
        mock_svc_cls.return_value.validate_code = AsyncMock(
            return_value=AffiliateCodeValidationResult(active=False)
        )
        with pytest.raises(ValueError, match="invalid_code"):
            await ApplyReferralCodeCommandHandler().handle(CMD)

    mock_uow.affiliate_outbox.enqueue.assert_not_awaited()

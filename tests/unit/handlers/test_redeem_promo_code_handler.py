"""Unit tests for RedeemPromoCodeCommandHandler."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.app.commands.promo_code.redeem_promo_code_command import RedeemPromoCodeCommand
from src.app.handlers.command_handlers.promo_code.redeem_promo_code_handler import (
    RedeemPromoCodeCommandHandler,
)
from src.app.queries.promo_code.validate_promo_code_query import PromoCodeValidationError
from src.infra.database.models.promo_code import PromoCode


def _make_promo(max_uses=100, current_uses=0, is_active=True):
    p = PromoCode()
    p.id = "promo-id-1"
    p.code = "SUMMER50"
    p.max_uses = max_uses
    p.current_uses = current_uses
    p.is_active = is_active
    p.expires_at = None
    p.rc_offering_id = "email"
    return p


def _mock_uow(promo=None, redemption=None):
    mock_uow = MagicMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.session = AsyncMock()

    mock_repo = AsyncMock()
    mock_repo.get_by_code_for_update = AsyncMock(return_value=promo)
    mock_repo.get_redemption = AsyncMock(return_value=redemption)
    mock_repo.create_redemption = AsyncMock()

    return mock_uow, mock_repo


@pytest.mark.asyncio
async def test_redeem_succeeds_for_valid_code():
    promo = _make_promo()
    mock_uow, mock_repo = _mock_uow(promo=promo)

    with patch(
        "src.app.handlers.command_handlers.promo_code.redeem_promo_code_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ), patch(
        "src.app.handlers.command_handlers.promo_code.redeem_promo_code_handler.PromoCodeRepository",
        return_value=mock_repo,
    ):
        handler = RedeemPromoCodeCommandHandler()
        await handler.handle(RedeemPromoCodeCommand(code="SUMMER50", user_id="user-123"))

    mock_repo.create_redemption.assert_awaited_once_with(promo_code=promo, user_id="user-123")


@pytest.mark.asyncio
async def test_redeem_raises_404_when_code_not_found():
    mock_uow, mock_repo = _mock_uow(promo=None)

    with patch(
        "src.app.handlers.command_handlers.promo_code.redeem_promo_code_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ), patch(
        "src.app.handlers.command_handlers.promo_code.redeem_promo_code_handler.PromoCodeRepository",
        return_value=mock_repo,
    ):
        handler = RedeemPromoCodeCommandHandler()
        with pytest.raises(PromoCodeValidationError) as exc_info:
            await handler.handle(RedeemPromoCodeCommand(code="BADCODE", user_id="user-123"))

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_redeem_raises_422_when_already_redeemed():
    from src.infra.database.models.promo_code import PromoCodeRedemption

    promo = _make_promo()
    existing = PromoCodeRedemption()
    mock_uow, mock_repo = _mock_uow(promo=promo, redemption=existing)

    with patch(
        "src.app.handlers.command_handlers.promo_code.redeem_promo_code_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ), patch(
        "src.app.handlers.command_handlers.promo_code.redeem_promo_code_handler.PromoCodeRepository",
        return_value=mock_repo,
    ):
        handler = RedeemPromoCodeCommandHandler()
        with pytest.raises(PromoCodeValidationError) as exc_info:
            await handler.handle(RedeemPromoCodeCommand(code="SUMMER50", user_id="user-123"))

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_redeem_raises_422_when_inactive():
    promo = _make_promo(is_active=False)
    mock_uow, mock_repo = _mock_uow(promo=promo)

    with patch(
        "src.app.handlers.command_handlers.promo_code.redeem_promo_code_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ), patch(
        "src.app.handlers.command_handlers.promo_code.redeem_promo_code_handler.PromoCodeRepository",
        return_value=mock_repo,
    ):
        handler = RedeemPromoCodeCommandHandler()
        with pytest.raises(PromoCodeValidationError) as exc_info:
            await handler.handle(RedeemPromoCodeCommand(code="SUMMER50", user_id="user-123"))

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_redeem_raises_422_when_max_uses_reached():
    promo = _make_promo(max_uses=10, current_uses=10)
    mock_uow, mock_repo = _mock_uow(promo=promo)

    with patch(
        "src.app.handlers.command_handlers.promo_code.redeem_promo_code_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ), patch(
        "src.app.handlers.command_handlers.promo_code.redeem_promo_code_handler.PromoCodeRepository",
        return_value=mock_repo,
    ):
        handler = RedeemPromoCodeCommandHandler()
        with pytest.raises(PromoCodeValidationError) as exc_info:
            await handler.handle(RedeemPromoCodeCommand(code="SUMMER50", user_id="user-123"))

    assert exc_info.value.status_code == 422
    assert "no longer available" in exc_info.value.detail


@pytest.mark.asyncio
async def test_redeem_raises_422_when_expired():
    from datetime import datetime, timezone, timedelta
    past = datetime.now(timezone.utc) - timedelta(days=1)
    promo = _make_promo()
    promo.expires_at = past
    mock_uow, mock_repo = _mock_uow(promo=promo)

    with patch(
        "src.app.handlers.command_handlers.promo_code.redeem_promo_code_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ), patch(
        "src.app.handlers.command_handlers.promo_code.redeem_promo_code_handler.PromoCodeRepository",
        return_value=mock_repo,
    ):
        handler = RedeemPromoCodeCommandHandler()
        with pytest.raises(PromoCodeValidationError) as exc_info:
            await handler.handle(RedeemPromoCodeCommand(code="SUMMER50", user_id="user-123"))

    assert exc_info.value.status_code == 422
    assert "expired" in exc_info.value.detail

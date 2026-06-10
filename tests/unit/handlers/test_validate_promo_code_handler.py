"""Unit tests for ValidatePromoCodeQueryHandler."""
from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app.handlers.query_handlers.promo_code.validate_promo_code_handler import (
    ValidatePromoCodeQueryHandler,
)
from src.app.queries.promo_code.validate_promo_code_query import (
    PromoCodeValidationError,
    ValidatePromoCodeQuery,
)
from src.infra.database.models.promo_code import PromoCode


def _make_promo(code="SUMMER50", max_uses=100, current_uses=0, is_active=True, expires_at=None):
    p = PromoCode()
    p.id = "promo-id-1"
    p.code = code
    p.max_uses = max_uses
    p.current_uses = current_uses
    p.is_active = is_active
    p.expires_at = expires_at
    p.rc_offering_id = "email"
    return p


def _mock_uow(promo=None, redemption=None):
    mock_uow = MagicMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.session = AsyncMock()

    mock_repo = AsyncMock()
    mock_repo.get_by_code = AsyncMock(return_value=promo)
    mock_repo.get_redemption = AsyncMock(return_value=redemption)
    mock_uow.promo_codes = mock_repo

    return mock_uow, mock_repo


@pytest.mark.asyncio
async def test_validate_returns_success_for_valid_code():
    promo = _make_promo()
    mock_uow, mock_repo = _mock_uow(promo=promo)

    with patch(
        "src.app.handlers.query_handlers.promo_code.validate_promo_code_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        handler = ValidatePromoCodeQueryHandler()
        result = await handler.handle(
            ValidatePromoCodeQuery(code="SUMMER50", user_id="user-123")
        )

    assert result["code"] == "SUMMER50"
    assert result["rc_offering_id"] == "email"
    assert result["is_valid"] is True


@pytest.mark.asyncio
async def test_validate_raises_404_when_code_not_found():
    mock_uow, mock_repo = _mock_uow(promo=None)

    with patch(
        "src.app.handlers.query_handlers.promo_code.validate_promo_code_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        handler = ValidatePromoCodeQueryHandler()
        with pytest.raises(PromoCodeValidationError) as exc_info:
            await handler.handle(
                ValidatePromoCodeQuery(code="BADCODE", user_id="user-123")
            )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_validate_raises_422_when_inactive():
    promo = _make_promo(is_active=False)
    mock_uow, mock_repo = _mock_uow(promo=promo)

    with patch(
        "src.app.handlers.query_handlers.promo_code.validate_promo_code_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        handler = ValidatePromoCodeQueryHandler()
        with pytest.raises(PromoCodeValidationError) as exc_info:
            await handler.handle(
                ValidatePromoCodeQuery(code="SUMMER50", user_id="user-123")
            )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_validate_raises_422_when_max_uses_reached():
    promo = _make_promo(max_uses=10, current_uses=10)
    mock_uow, mock_repo = _mock_uow(promo=promo)

    with patch(
        "src.app.handlers.query_handlers.promo_code.validate_promo_code_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        handler = ValidatePromoCodeQueryHandler()
        with pytest.raises(PromoCodeValidationError) as exc_info:
            await handler.handle(
                ValidatePromoCodeQuery(code="SUMMER50", user_id="user-123")
            )

    assert exc_info.value.status_code == 422
    assert "no longer available" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_raises_422_when_already_redeemed():
    from src.infra.database.models.promo_code import PromoCodeRedemption

    promo = _make_promo()
    existing_redemption = PromoCodeRedemption()
    mock_uow, mock_repo = _mock_uow(promo=promo, redemption=existing_redemption)

    with patch(
        "src.app.handlers.query_handlers.promo_code.validate_promo_code_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        handler = ValidatePromoCodeQueryHandler()
        with pytest.raises(PromoCodeValidationError) as exc_info:
            await handler.handle(
                ValidatePromoCodeQuery(code="SUMMER50", user_id="user-123")
            )

    assert exc_info.value.status_code == 422
    assert "already used" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_raises_422_when_expired():
    from datetime import datetime, timedelta
    past = datetime.now(UTC) - timedelta(days=1)
    promo = _make_promo(expires_at=past)
    mock_uow, mock_repo = _mock_uow(promo=promo)

    with patch(
        "src.app.handlers.query_handlers.promo_code.validate_promo_code_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        handler = ValidatePromoCodeQueryHandler()
        with pytest.raises(PromoCodeValidationError) as exc_info:
            await handler.handle(ValidatePromoCodeQuery(code="SUMMER50", user_id="user-123"))

    assert exc_info.value.status_code == 422
    assert "expired" in exc_info.value.detail

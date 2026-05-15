"""Unit tests for PromoCodeRepository."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from src.infra.database.models.promo_code import PromoCode, PromoCodeRedemption
from src.infra.repositories.promo_code_repository import PromoCodeRepository


def _make_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session


def _make_promo(
    code="SUMMER50",
    max_uses=100,
    current_uses=0,
    is_active=True,
    expires_at=None,
    id="promo-id-123",
):
    p = PromoCode()
    p.id = id
    p.code = code
    p.max_uses = max_uses
    p.current_uses = current_uses
    p.is_active = is_active
    p.expires_at = expires_at
    p.rc_offering_id = "email"
    return p


@pytest.mark.asyncio
async def test_get_by_code_returns_promo_when_exists():
    session = _make_session()
    promo = _make_promo()
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = promo
    session.execute = AsyncMock(return_value=result_mock)

    repo = PromoCodeRepository(session)
    found = await repo.get_by_code("SUMMER50")

    assert found is promo


@pytest.mark.asyncio
async def test_get_by_code_returns_none_when_missing():
    session = _make_session()
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = None
    session.execute = AsyncMock(return_value=result_mock)

    repo = PromoCodeRepository(session)
    found = await repo.get_by_code("NOTEXIST")

    assert found is None


@pytest.mark.asyncio
async def test_get_redemption_returns_none_when_no_redemption():
    session = _make_session()
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = None
    session.execute = AsyncMock(return_value=result_mock)

    repo = PromoCodeRepository(session)
    found = await repo.get_redemption(promo_code_id="promo-id-123", user_id="user-abc")

    assert found is None


@pytest.mark.asyncio
async def test_create_redemption_increments_uses_and_adds_row():
    session = _make_session()
    promo = _make_promo(current_uses=5)

    repo = PromoCodeRepository(session)
    redemption = await repo.create_redemption(promo_code=promo, user_id="user-abc")

    assert promo.current_uses == 6
    assert redemption.promo_code_id == "promo-id-123"
    assert redemption.user_id == "user-abc"
    session.add.assert_called_once_with(redemption)

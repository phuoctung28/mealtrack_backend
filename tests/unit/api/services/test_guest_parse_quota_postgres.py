"""Unit tests for GuestParseQuotaService (Postgres-backed) logic."""
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.api.services.guest_parse_quota import (
    GuestParseQuotaService,
    QuotaAlreadyUsedError,
    QuotaInFlightError,
    QuotaUnavailableError,
    _hash_install_id,
    validate_install_id,
)
from src.domain.utils.timezone_utils import utc_now


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_savepoint(*, raises_on_flush: Exception | None = None):
    """Async context manager mock for session.begin_nested()."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=MagicMock())
    # __aexit__ returns False → exception propagates; True → suppresses
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_session(
    *,
    flush_raises: "Exception | list[Exception | None] | None" = None,
    execute_row: MagicMock | None = None,
) -> MagicMock:
    """Build a minimal AsyncSession mock.

    flush_raises: single exception (raised every call), list (one per call, None=ok),
    or None (always succeeds).
    """
    session = MagicMock()
    session.add = MagicMock()
    session.delete = AsyncMock()

    if isinstance(flush_raises, list):
        _effects = list(flush_raises)

        async def _flush(*args, **kwargs):
            exc = _effects.pop(0) if _effects else None
            if exc is not None:
                raise exc
    elif flush_raises is not None:
        _exc = flush_raises

        async def _flush(*args, **kwargs):
            raise _exc
    else:
        async def _flush(*args, **kwargs):
            pass

    session.flush = _flush

    if execute_row is not None:
        result = MagicMock()
        result.scalar_one = MagicMock(return_value=execute_row)
        result.scalar_one_or_none = MagicMock(return_value=execute_row)
        session.execute = AsyncMock(return_value=result)
    else:
        session.execute = AsyncMock()

    return session


def _reserved_row(*, expired: bool = False) -> MagicMock:
    row = MagicMock()
    row.status = "reserved"
    row.reserved_until = utc_now() + timedelta(seconds=-60 if expired else 30)
    return row


def _completed_row() -> MagicMock:
    row = MagicMock()
    row.status = "completed"
    row.reserved_until = None
    return row


# ---------------------------------------------------------------------------
# validate_install_id
# ---------------------------------------------------------------------------

def test_validate_install_id_valid():
    assert validate_install_id("abc12345") is True
    assert validate_install_id("a" * 128) is True


def test_validate_install_id_invalid():
    assert validate_install_id("abc") is False      # too short
    assert validate_install_id("a" * 129) is False  # too long
    assert validate_install_id("has space!") is False


# ---------------------------------------------------------------------------
# reserve — first insert succeeds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reserve_first_time_returns_hash():
    session = _make_session()
    savepoint = _make_savepoint()
    session.begin_nested = MagicMock(return_value=savepoint)

    svc = GuestParseQuotaService(session, hash_secret="test")
    result = await svc.reserve("install-abc12345")

    expected = _hash_install_id("install-abc12345", "test")
    assert result == expected
    session.add.assert_called_once()


# ---------------------------------------------------------------------------
# reserve — row exists, in-flight
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reserve_in_flight_raises():
    session = _make_session(
        flush_raises=IntegrityError("unique", {}, None),
        execute_row=_reserved_row(expired=False),
    )
    savepoint = _make_savepoint()
    session.begin_nested = MagicMock(return_value=savepoint)

    svc = GuestParseQuotaService(session, hash_secret="test")
    with pytest.raises(QuotaInFlightError):
        await svc.reserve("install-abc12345")


# ---------------------------------------------------------------------------
# reserve — row exists, completed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reserve_completed_raises_already_used():
    session = _make_session(
        flush_raises=IntegrityError("unique", {}, None),
        execute_row=_completed_row(),
    )
    savepoint = _make_savepoint()
    session.begin_nested = MagicMock(return_value=savepoint)

    svc = GuestParseQuotaService(session, hash_secret="test")
    with pytest.raises(QuotaAlreadyUsedError):
        await svc.reserve("install-abc12345")


# ---------------------------------------------------------------------------
# reserve — expired reservation is reclaimed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reserve_expired_reclaims_slot():
    row = _reserved_row(expired=True)
    session = _make_session(
        # First flush (inside savepoint) fails — row exists; second flush (update) succeeds
        flush_raises=[IntegrityError("unique", {}, None), None],
        execute_row=row,
    )
    savepoint = _make_savepoint()
    session.begin_nested = MagicMock(return_value=savepoint)

    svc = GuestParseQuotaService(session, hash_secret="test")
    result = await svc.reserve("install-abc12345")

    expected = _hash_install_id("install-abc12345", "test")
    assert result == expected
    assert row.status == "reserved"
    assert row.reserved_until is not None


# ---------------------------------------------------------------------------
# reserve — DB failure raises QuotaUnavailableError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reserve_db_failure_raises_unavailable():
    session = _make_session(flush_raises=SQLAlchemyError("conn lost"))
    savepoint = _make_savepoint()
    session.begin_nested = MagicMock(return_value=savepoint)

    svc = GuestParseQuotaService(session, hash_secret="test")
    with pytest.raises(QuotaUnavailableError):
        await svc.reserve("install-abc12345")


# ---------------------------------------------------------------------------
# mark_completed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mark_completed_updates_row():
    row = _reserved_row()
    session = _make_session(execute_row=row)

    svc = GuestParseQuotaService(session, hash_secret="test")
    await svc.mark_completed("somehash")

    assert row.status == "completed"
    assert row.reserved_until is None
    assert row.completed_at is not None


# ---------------------------------------------------------------------------
# release_reservation — reserved row is deleted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_release_reservation_deletes_reserved_row():
    row = _reserved_row()
    session = _make_session(execute_row=row)

    svc = GuestParseQuotaService(session, hash_secret="test")
    await svc.release_reservation("somehash")

    session.delete.assert_awaited_once_with(row)


# ---------------------------------------------------------------------------
# release_reservation — completed row is NOT deleted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_release_reservation_skips_completed_row():
    row = _completed_row()
    session = _make_session(execute_row=row)

    svc = GuestParseQuotaService(session, hash_secret="test")
    await svc.release_reservation("somehash")

    session.delete.assert_not_awaited()

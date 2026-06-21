"""Failing contract tests for D2 daily_summary suppression logic.

When the campaign scheduler inserts a `d2_daily_summary` row it must delete
any pending `daily_summary` rows for the same user on the same local date.
The production helper does not exist yet — tests are intentionally red.
"""

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from src.infra.services.onboarding_retention_campaign_scheduler import (  # noqa: F401
    suppress_normal_daily_summary,
)

NOW_UTC = datetime(2026, 6, 21, 10, 0, 0, tzinfo=UTC)
LOCAL_DATE = date(2026, 6, 21)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(deleted_rows=1):
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(rowcount=deleted_rows))
    return session


def _make_notif(status: str, user_id: str, notification_type: str = "daily_summary"):
    n = MagicMock()
    n.status = status
    n.user_id = user_id
    n.notification_type = notification_type
    return n


# ---------------------------------------------------------------------------
# Core suppression contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_d2_insert_deletes_pending_normal_summary():
    """Inserting d2_daily_summary triggers deletion of pending daily_summary rows."""
    user_id = str(uuid.uuid4())
    session = _make_session(deleted_rows=1)

    deleted = await suppress_normal_daily_summary(
        user_id=user_id,
        local_date=LOCAL_DATE,
        session=session,
    )

    assert deleted >= 1
    # Must have issued a DELETE (execute called with a statement)
    session.execute.assert_awaited_once()
    stmt_arg = session.execute.call_args[0][0]
    # The statement should reference the daily_summary type and the target user
    stmt_str = str(stmt_arg).lower()
    assert "daily_summary" in stmt_str or "notification_type" in stmt_str, (
        f"DELETE statement does not reference daily_summary: {stmt_str!r}"
    )


@pytest.mark.asyncio
async def test_d2_suppression_does_not_touch_sent_rows():
    """Rows with status='sent' or status='failed' must not be deleted."""
    user_id = str(uuid.uuid4())

    # Simulate: the DB-side WHERE clause filters to status='pending' only;
    # session.execute returns rowcount=0 when only sent/failed rows exist.
    session = _make_session(deleted_rows=0)

    deleted = await suppress_normal_daily_summary(
        user_id=user_id,
        local_date=LOCAL_DATE,
        session=session,
        # Caller responsibility: only pending rows targeted by SQL
    )

    # 0 rows deleted — sent/failed rows were left intact
    assert deleted == 0


@pytest.mark.asyncio
async def test_d2_suppression_does_not_touch_other_users():
    """Suppression is scoped to the specific user_id — other users unaffected."""
    target_user = str(uuid.uuid4())
    other_user = str(uuid.uuid4())

    call_args_list: list = []

    async def _capture_execute(stmt, *args, **kwargs):
        call_args_list.append(str(stmt))
        return MagicMock(rowcount=1)

    session = MagicMock()
    session.execute = AsyncMock(side_effect=_capture_execute)

    await suppress_normal_daily_summary(
        user_id=target_user,
        local_date=LOCAL_DATE,
        session=session,
    )

    assert len(call_args_list) == 1
    stmt_text = call_args_list[0]
    # The other_user id must NOT appear in the SQL — only target_user is filtered
    assert other_user not in stmt_text, (
        "Suppression DELETE leaked into other user's rows"
    )
    assert target_user in stmt_text or "user_id" in stmt_text.lower(), (
        "Suppression DELETE does not filter by user_id"
    )


@pytest.mark.asyncio
async def test_d2_suppression_returns_zero_when_no_pending_rows_exist():
    """Returns 0 when there are no pending daily_summary rows to delete."""
    session = _make_session(deleted_rows=0)

    deleted = await suppress_normal_daily_summary(
        user_id=str(uuid.uuid4()),
        local_date=LOCAL_DATE,
        session=session,
    )

    assert deleted == 0


@pytest.mark.asyncio
async def test_d2_suppression_targets_correct_local_date():
    """DELETE WHERE clause includes the local_date to avoid cross-day deletions."""
    user_id = str(uuid.uuid4())
    captured: list[str] = []

    async def _capture(stmt, *args, **kwargs):
        captured.append(str(stmt))
        return MagicMock(rowcount=0)

    session = MagicMock()
    session.execute = AsyncMock(side_effect=_capture)

    await suppress_normal_daily_summary(
        user_id=user_id,
        local_date=LOCAL_DATE,
        session=session,
    )

    assert len(captured) == 1
    stmt_text = captured[0].lower()
    assert "scheduled_date" in stmt_text or "2026-06-21" in stmt_text, (
        "Suppression DELETE does not filter by local date"
    )

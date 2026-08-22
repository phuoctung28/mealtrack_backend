from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.app.commands.cheat_day import MarkCheatDayCommand, UnmarkCheatDayCommand
from src.app.handlers.command_handlers.mark_cheat_day_command_handler import (
    MarkCheatDayCommandHandler,
)
from src.app.handlers.command_handlers.unmark_cheat_day_command_handler import (
    UnmarkCheatDayCommandHandler,
)


class TrackingUnitOfWork:
    def __init__(self, events: list[str], existing=None):
        self.events = events
        self.cheat_days = SimpleNamespace(
            find_by_user_and_date=AsyncMock(return_value=existing),
            add=AsyncMock(),
            delete=AsyncMock(),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        self.events.append("uow_exit")
        return False

    async def commit(self):
        self.events.append("commit")

    async def rollback(self):
        self.events.append("rollback")


@pytest.mark.asyncio
async def test_mark_cheat_day_publishes_invalidation_after_commit_and_uow_exit():
    events: list[str] = []
    uow = TrackingUnitOfWork(events)
    cache_invalidation = SimpleNamespace(
        after_cheat_day_write=AsyncMock(side_effect=lambda *_: events.append("cache"))
    )
    target_date = date(2026, 8, 23)

    with (
        patch(
            "src.app.handlers.command_handlers.mark_cheat_day_command_handler.resolve_user_timezone_async",
            new=AsyncMock(return_value="UTC"),
        ),
        patch(
            "src.app.handlers.command_handlers.mark_cheat_day_command_handler.user_today",
            return_value=date(2026, 8, 22),
        ),
    ):
        await MarkCheatDayCommandHandler(uow, cache_invalidation).handle(
            MarkCheatDayCommand(user_id="u1", date=target_date)
        )

    assert events == ["commit", "uow_exit", "cache"]


@pytest.mark.asyncio
async def test_unmark_cheat_day_publishes_invalidation_after_commit_and_uow_exit():
    events: list[str] = []
    uow = TrackingUnitOfWork(events, existing=SimpleNamespace(cheat_day_id="cheat-1"))
    cache_invalidation = SimpleNamespace(
        after_cheat_day_write=AsyncMock(side_effect=lambda *_: events.append("cache"))
    )
    target_date = date(2026, 8, 22)

    await UnmarkCheatDayCommandHandler(uow, cache_invalidation).handle(
        UnmarkCheatDayCommand(user_id="u1", date=target_date)
    )

    assert events == ["commit", "uow_exit", "cache"]

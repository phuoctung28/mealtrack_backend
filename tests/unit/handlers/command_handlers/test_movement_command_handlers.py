from datetime import date, datetime, timezone

import pytest

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.app.commands.movement import DeleteMovementEntryCommand, LogMovementCommand
from src.app.handlers.command_handlers.delete_movement_entry_command_handler import (
    DeleteMovementEntryCommandHandler,
)
from src.app.handlers.command_handlers import log_movement_command_handler
from src.app.handlers.command_handlers.log_movement_command_handler import (
    LogMovementCommandHandler,
    _validate_log_movement,
)


def test_validate_log_movement_accepts_catalog_activity():
    _validate_log_movement(
        LogMovementCommand(
            user_id="user-1",
            activity_id="badminton",
            activity_name="Badminton",
            duration_min=60,
            kcal_burned=231.0,
            intensity="moderate",
            include_in_balance=True,
        )
    )


def test_validate_log_movement_rejects_unknown_activity_id():
    with pytest.raises(ValidationException) as exc:
        _validate_log_movement(
            LogMovementCommand(
                user_id="user-1",
                activity_id="unknown",
                activity_name="Unknown",
                duration_min=60,
                kcal_burned=231.0,
                intensity="moderate",
                include_in_balance=True,
            )
        )

    assert exc.value.error_code == "INVALID_ACTIVITY"


@pytest.mark.parametrize("activity_name", ["", "   ", "x" * 101])
def test_validate_log_movement_rejects_invalid_activity_name(activity_name):
    with pytest.raises(ValidationException) as exc:
        _validate_log_movement(
            LogMovementCommand(
                user_id="user-1",
                activity_id=None,
                activity_name=activity_name,
                duration_min=60,
                kcal_burned=231.0,
                intensity="moderate",
                include_in_balance=True,
            )
        )

    assert exc.value.error_code == "INVALID_ACTIVITY"


@pytest.mark.parametrize(
    ("duration_min", "error_code"),
    [(0, "INVALID_DURATION"), (-1, "INVALID_DURATION"), (601, "INVALID_DURATION")],
)
def test_validate_log_movement_rejects_invalid_duration(duration_min, error_code):
    with pytest.raises(ValidationException) as exc:
        _validate_log_movement(
            LogMovementCommand(
                user_id="user-1",
                activity_id="badminton",
                activity_name="Badminton",
                duration_min=duration_min,
                kcal_burned=100.0,
                intensity="moderate",
                include_in_balance=True,
            )
        )

    assert exc.value.error_code == error_code


def test_validate_log_movement_accepts_zero_kcal():
    _validate_log_movement(
        LogMovementCommand(
            user_id="user-1",
            activity_id=None,
            activity_name="Custom walk",
            duration_min=60,
            kcal_burned=0.0,
            intensity="moderate",
            include_in_balance=True,
        )
    )


def test_validate_log_movement_rejects_negative_kcal():
    with pytest.raises(ValidationException) as exc:
        _validate_log_movement(
            LogMovementCommand(
                user_id="user-1",
                activity_id="badminton",
                activity_name="Badminton",
                duration_min=60,
                kcal_burned=-1.0,
                intensity="moderate",
                include_in_balance=True,
            )
        )

    assert exc.value.error_code == "INVALID_KCAL"


def test_validate_log_movement_rejects_invalid_intensity():
    with pytest.raises(ValidationException) as exc:
        _validate_log_movement(
            LogMovementCommand(
                user_id="user-1",
                activity_id="badminton",
                activity_name="Badminton",
                duration_min=60,
                kcal_burned=231.0,
                intensity="extreme",
                include_in_balance=True,
            )
        )

    assert exc.value.error_code == "INVALID_INTENSITY"


def test_validate_log_movement_rejects_preset_activity_unsupported_intensity(
    monkeypatch,
):
    monkeypatch.setattr(
        log_movement_command_handler,
        "get_activity",
        lambda activity_id: {"id": activity_id},
    )
    monkeypatch.setattr(
        log_movement_command_handler,
        "get_met",
        lambda activity_id, intensity: None,
    )

    with pytest.raises(ValidationException) as exc:
        _validate_log_movement(
            LogMovementCommand(
                user_id="user-1",
                activity_id="badminton",
                activity_name="Badminton",
                duration_min=60,
                kcal_burned=231.0,
                intensity="moderate",
                include_in_balance=True,
            )
        )

    assert exc.value.error_code == "INVALID_INTENSITY"


class _FakeUsers:
    async def find_by_id(self, user_id):
        return None


class _FakeMovementEntries:
    def __init__(self):
        self.added = []
        self.deleted = True

    async def add(self, entry):
        self.added.append(entry)
        return entry

    async def delete(self, user_id, entry_id):
        return self.deleted


class _FakeUow:
    def __init__(self):
        self.users = _FakeUsers()
        self.movement_entries = _FakeMovementEntries()
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def commit(self):
        self.committed = True


class _FakeCache:
    def __init__(self):
        self.invalidated = []
        self.patterns = []

    async def invalidate(self, key):
        self.invalidated.append(key)
        return True

    async def invalidate_pattern(self, pattern):
        self.patterns.append(pattern)
        return 1


@pytest.mark.asyncio
async def test_log_movement_handler_saves_entry_and_invalidates_daily_caches():
    uow = _FakeUow()
    cache = _FakeCache()
    handler = LogMovementCommandHandler(uow=uow, cache_service=cache)

    result = await handler.handle(
        LogMovementCommand(
            user_id="user-1",
            activity_id="badminton",
            activity_name="Badminton",
            duration_min=45,
            kcal_burned=200.5,
            intensity="moderate",
            include_in_balance=True,
            target_date=date(2026, 5, 30),
            header_timezone="Asia/Ho_Chi_Minh",
        )
    )

    saved = uow.movement_entries.added[0]
    assert saved.user_id == "user-1"
    assert saved.activity_id == "badminton"
    assert saved.logged_at == datetime(2026, 5, 30, 5, 0, tzinfo=timezone.utc)
    assert uow.committed is True
    assert result["id"] == saved.id
    assert result["logged_at"] == "2026-05-30T05:00:00+00:00"
    assert "user:user-1:macros:2026-05-30" in cache.invalidated
    assert "user:user-1:activities:2026-05-30:*" in cache.patterns


@pytest.mark.asyncio
async def test_delete_movement_handler_raises_not_found_when_delete_returns_false():
    uow = _FakeUow()
    uow.movement_entries.deleted = False
    handler = DeleteMovementEntryCommandHandler(uow=uow)

    with pytest.raises(ResourceNotFoundException) as exc:
        await handler.handle(
            DeleteMovementEntryCommand(user_id="user-1", entry_id="missing")
        )

    assert exc.value.error_code == "ENTRY_NOT_FOUND"

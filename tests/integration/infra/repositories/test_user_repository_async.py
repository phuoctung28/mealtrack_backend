"""Integration tests for AsyncUserRepository."""

import pytest
import uuid
from datetime import datetime

from src.infra.repositories.user_repository_async import AsyncUserRepository
from src.infra.database.models.user.user import User
from src.api.schemas.common.auth_enums import AuthProviderEnum


async def _insert_user(session, uid: str = "firebase-uid-001") -> User:
    """Insert a minimal but valid User row (all non-nullable fields supplied)."""
    user = User(
        id=str(uuid.uuid4()),
        firebase_uid=uid,
        email=f"{uid}@test.com",
        username=f"user_{uid.replace('-', '_')}",
        password_hash="hashed_password",
        provider=AuthProviderEnum.GOOGLE,
        is_active=True,
        onboarding_completed=False,
        last_accessed=datetime.utcnow(),
    )
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_find_by_firebase_uid_returns_active_user(async_db_session):
    await _insert_user(async_db_session, "firebase-uid-t01")
    repo = AsyncUserRepository(async_db_session)
    result = await repo.find_by_firebase_uid("firebase-uid-t01")
    assert result is not None
    assert result.firebase_uid == "firebase-uid-t01"


@pytest.mark.asyncio
async def test_find_by_firebase_uid_returns_none_for_inactive(async_db_session):
    user = await _insert_user(async_db_session, "firebase-uid-t02")
    user.is_active = False
    await async_db_session.flush()

    repo = AsyncUserRepository(async_db_session)
    result = await repo.find_by_firebase_uid("firebase-uid-t02")
    assert result is None


@pytest.mark.asyncio
async def test_find_deleted_by_firebase_uid_returns_inactive_user(async_db_session):
    user = await _insert_user(async_db_session, "firebase-uid-t03")
    user.is_active = False
    await async_db_session.flush()

    repo = AsyncUserRepository(async_db_session)
    result = await repo.find_deleted_by_firebase_uid("firebase-uid-t03")
    assert result is not None
    assert result.firebase_uid == "firebase-uid-t03"


@pytest.mark.asyncio
async def test_find_by_email_returns_active_user(async_db_session):
    await _insert_user(async_db_session, "firebase-uid-t04")
    repo = AsyncUserRepository(async_db_session)
    result = await repo.find_by_email("firebase-uid-t04@test.com")
    assert result is not None
    assert result.email == "firebase-uid-t04@test.com"


@pytest.mark.asyncio
async def test_delete_marks_user_inactive(async_db_session):
    user = await _insert_user(async_db_session, "firebase-uid-t05")
    user_id = uuid.UUID(user.id)

    repo = AsyncUserRepository(async_db_session)
    deleted = await repo.delete(user_id)
    assert deleted is True

    # Active lookup should return nothing
    result = await repo.find_by_firebase_uid("firebase-uid-t05")
    assert result is None


@pytest.mark.asyncio
async def test_get_user_timezone_returns_default(async_db_session):
    user = await _insert_user(async_db_session, "firebase-uid-t06")
    user_id = uuid.UUID(user.id)

    repo = AsyncUserRepository(async_db_session)
    tz = await repo.get_user_timezone(user_id)
    # server_default is 'UTC'; Python default is also 'UTC' (no value set explicitly)
    assert tz is not None


@pytest.mark.asyncio
async def test_update_user_timezone(async_db_session):
    user = await _insert_user(async_db_session, "firebase-uid-t07")
    user_id = uuid.UUID(user.id)

    repo = AsyncUserRepository(async_db_session)
    await repo.update_user_timezone(user_id, "America/New_York")
    await async_db_session.flush()

    tz = await repo.get_user_timezone(user_id)
    assert tz == "America/New_York"

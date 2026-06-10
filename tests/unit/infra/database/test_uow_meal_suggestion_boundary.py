import pytest

from src.infra.database.uow_async import UnavailableMealSuggestionSessionStore


@pytest.mark.asyncio
async def test_db_uow_meal_suggestion_store_explains_redis_boundary():
    store = UnavailableMealSuggestionSessionStore()

    with pytest.raises(RuntimeError, match="Redis-backed transient state"):
        await store.get_session("session_1")

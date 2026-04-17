"""Unit tests: GetUserProfileQueryHandler cache hit/miss behaviour."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.app.queries.user import GetUserProfileQuery
from src.app.handlers.query_handlers.get_user_profile_query_handler import (
    GetUserProfileQueryHandler,
)
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.user.tdee import Goal, MacroTargets, TdeeResponse


@pytest.mark.asyncio
async def test_returns_cached_value_on_hit():
    """On a cache hit, no DB session is opened."""
    cached_payload = {"profile": {"user_id": "u1"}, "tdee": {"calories": 2000}}
    cache_service = MagicMock()
    cache_service.get_json = AsyncMock(return_value=cached_payload)
    cache_service.set_json = AsyncMock()

    handler = GetUserProfileQueryHandler(cache_service=cache_service)
    query = GetUserProfileQuery(user_id="u1")

    with patch("src.app.handlers.query_handlers.get_user_profile_query_handler.UnitOfWork") as mock_uow:
        result = await handler.handle(query)

    assert result == cached_payload
    mock_uow.assert_not_called()
    cache_service.set_json.assert_not_awaited()


@pytest.mark.asyncio
async def test_stores_result_in_cache_on_miss():
    """On a cache miss the result is written to Redis after DB fetch."""
    cache_service = MagicMock()
    cache_service.get_json = AsyncMock(return_value=None)  # miss
    cache_service.set_json = AsyncMock()

    handler = GetUserProfileQueryHandler(cache_service=cache_service)
    query = GetUserProfileQuery(user_id="u1")

    db_result = {"profile": {"user_id": "u1"}, "tdee": {"calories": 2000}}
    with patch.object(handler, "_fetch_from_db", AsyncMock(return_value=db_result)):
        result = await handler.handle(query)

    assert result == db_result
    cache_service.set_json.assert_awaited_once()
    call_args = cache_service.set_json.call_args[0]
    expected_key, expected_ttl = CacheKeys.user_profile("u1")
    assert call_args[0] == expected_key
    assert call_args[2] == expected_ttl


@pytest.mark.asyncio
async def test_works_without_cache_service():
    """Handler functions normally when no cache_service is provided."""
    handler = GetUserProfileQueryHandler(cache_service=None)
    query = GetUserProfileQuery(user_id="u1")

    db_result = {"profile": {"user_id": "u1"}, "tdee": {}}
    with patch.object(handler, "_fetch_from_db", AsyncMock(return_value=db_result)):
        result = await handler.handle(query)

    assert result == db_result


def test_fetch_from_db_tdee_is_json_serializable():
    """_fetch_from_db result round-trips through json.dumps without raising.

    TdeeResponse is a dataclass with enum fields; _fetch_from_db must call
    .to_dict() so the payload is JSON-safe before set_json stores it.
    """
    tdee_response = TdeeResponse(
        bmr=1700.0,
        tdee=2300.0,
        goal=Goal.CUT,
        macros=MacroTargets(calories=1900.0, protein=180.0, fat=65.0, carbs=170.0),
        formula_used="Mifflin-St Jeor",
    )
    profile_data = {
        "id": 1,
        "user_id": "u1",
        "age": 30,
        "gender": "male",
        "height_cm": 175.0,
        "weight_kg": 80.0,
        "body_fat_percentage": None,
        "job_type": "desk",
        "training_days_per_week": 4,
        "training_minutes_per_session": 60,
        "training_level": "intermediate",
        "fitness_goal": "cut",
        "target_weight_kg": 75.0,
        "meals_per_day": 3,
        "snacks_per_day": 1,
        "dietary_preferences": [],
        "health_conditions": [],
        "allergies": [],
        "created_at": None,
        "updated_at": None,
    }
    result = {
        "profile": profile_data,
        "tdee": tdee_response.to_dict(),
    }
    # Must not raise TypeError for non-serializable types (e.g. Enum or dataclass)
    serialized = json.dumps(result)
    parsed = json.loads(serialized)
    assert parsed["tdee"]["goal"] == "cut"
    assert parsed["tdee"]["bmr"] == 1700.0
    assert parsed["tdee"]["macros"]["protein"] == 180.0
    assert parsed["tdee"]["formula_used"] == "Mifflin-St Jeor"

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.domain.model.meal_suggestion import (
    Ingredient,
    MacroEstimate,
    MealSuggestion,
    MealType,
    RecipeStep,
    SuggestionSession,
    SuggestionStatus,
)
from src.infra.repositories.meal_suggestion_repository import MealSuggestionRepository


@pytest.fixture
def session():
    return SuggestionSession(
        id="sess_1",
        user_id="user_1",
        meal_type="dinner",
        meal_portion_type="M",
        target_calories=600,
        ingredients=["chicken"],
        cooking_time_minutes=20,
        shown_suggestion_ids=[],
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=4),
    )


@pytest.fixture
def suggestion(session):
    return MealSuggestion(
        id="sug_1",
        session_id=session.id,
        user_id=session.user_id,
        meal_name="Grilled Chicken",
        description="desc",
        meal_type=MealType.DINNER,
        macros=MacroEstimate(calories=500, protein=40.0, carbs=20.0, fat=25.0),
        ingredients=[Ingredient(name="chicken", amount=200.0, unit="g")],
        recipe_steps=[RecipeStep(step=1, instruction="cook", duration_minutes=10)],
        prep_time_minutes=15,
        confidence_score=0.9,
        status=SuggestionStatus.PENDING,
        generated_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_save_and_get_session_roundtrip(session):
    redis = SimpleNamespace(
        set=AsyncMock(),
        get=AsyncMock(return_value=None),
        delete=AsyncMock(),
        delete_pattern=AsyncMock(return_value=0),
        client=None,
    )
    repo = MealSuggestionRepository(redis)

    await repo.save_session(session)
    redis.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_session_uses_remaining_ttl_when_available(session):
    client = SimpleNamespace(ttl=AsyncMock(return_value=123))
    redis = SimpleNamespace(
        set=AsyncMock(),
        get=AsyncMock(return_value=None),
        delete=AsyncMock(),
        delete_pattern=AsyncMock(return_value=0),
        client=client,
    )
    repo = MealSuggestionRepository(redis)
    await repo.update_session(session)

    # called with ttl from ttl()
    _, kwargs = redis.set.call_args
    assert kwargs["ttl"] == 123


@pytest.mark.asyncio
async def test_update_session_falls_back_to_default_ttl_when_expired(session):
    client = SimpleNamespace(ttl=AsyncMock(return_value=-1))
    redis = SimpleNamespace(
        set=AsyncMock(),
        get=AsyncMock(return_value=None),
        delete=AsyncMock(),
        delete_pattern=AsyncMock(return_value=0),
        client=client,
    )
    repo = MealSuggestionRepository(redis)
    await repo.update_session(session)

    _, kwargs = redis.set.call_args
    assert kwargs["ttl"] == repo.TTL_SECONDS


@pytest.mark.asyncio
async def test_save_session_with_suggestions_skips_without_client(session, suggestion):
    redis = SimpleNamespace(
        set=AsyncMock(),
        get=AsyncMock(return_value=None),
        delete=AsyncMock(),
        delete_pattern=AsyncMock(return_value=0),
        client=None,
    )
    repo = MealSuggestionRepository(redis)
    await repo.save_session_with_suggestions(session, [suggestion])
    # no client => no pipeline calls
    redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_save_session_with_suggestions_uses_pipeline(session, suggestion):
    pipe = SimpleNamespace(set=AsyncMock(), execute=AsyncMock())

    class _PipelineCtx:
        async def __aenter__(self):
            return pipe

        async def __aexit__(self, exc_type, exc, tb):
            return False

    client = SimpleNamespace(pipeline=lambda transaction=False: _PipelineCtx())
    redis = SimpleNamespace(
        set=AsyncMock(),
        get=AsyncMock(return_value=None),
        delete=AsyncMock(),
        delete_pattern=AsyncMock(return_value=0),
        client=client,
    )

    repo = MealSuggestionRepository(redis)
    await repo.save_session_with_suggestions(session, [suggestion])

    # session + 1 suggestion
    assert pipe.set.call_count == 2
    pipe.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_suggestion_searches_keys_and_deserializes(session, suggestion):
    client = SimpleNamespace(keys=AsyncMock(return_value=[f"suggestion:{session.id}:{suggestion.id}"]))
    serialized = MealSuggestionRepository(SimpleNamespace())._serialize_suggestion(suggestion)
    redis = SimpleNamespace(
        set=AsyncMock(),
        get=AsyncMock(return_value=serialized),
        delete=AsyncMock(),
        delete_pattern=AsyncMock(return_value=0),
        client=client,
    )
    repo = MealSuggestionRepository(redis)
    out = await repo.get_suggestion(suggestion.id)
    assert out is not None
    assert out.id == suggestion.id


@pytest.mark.asyncio
async def test_delete_session_deletes_session_key_and_pattern(session):
    redis = SimpleNamespace(
        set=AsyncMock(),
        get=AsyncMock(return_value=None),
        delete=AsyncMock(),
        delete_pattern=AsyncMock(return_value=3),
        client=None,
    )
    repo = MealSuggestionRepository(redis)
    await repo.delete_session(session.id)
    redis.delete.assert_awaited_once()
    redis.delete_pattern.assert_awaited_once()


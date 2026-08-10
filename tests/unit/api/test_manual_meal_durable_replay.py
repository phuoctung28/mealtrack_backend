"""Route-level durable replay behavior for POST /v1/meals/manual."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.api.routes.v1.meals_manual_text import create_manual_meal
from src.api.schemas.request.meal_requests import (
    CreateManualMealFromFoodsRequest,
    ManualMealItemRequest,
)
from src.infra.services.durable_write_service import DurableWriteRecord


def _payload() -> CreateManualMealFromFoodsRequest:
    return CreateManualMealFromFoodsRequest(
        dish_name="Oats",
        meal_type="breakfast",
        target_date="2026-08-11",
        source="manual",
        items=[
            ManualMealItemRequest(
                fdc_id=123,
                name="Oats",
                quantity=40,
                unit="g",
            )
        ],
    )


@pytest.mark.asyncio
async def test_manual_meal_replays_stored_response():
    stored = DurableWriteRecord(
        request_fingerprint="abc",
        response_status_code=200,
        response_body={
            "meal_id": "meal-1",
            "status": "success",
            "message": "Meal 'Oats' created successfully",
            "created_at": "2026-08-11T00:00:00+00:00",
            "meal_detail": None,
        },
        resource_id="meal-1",
    )
    with (
        patch(
            "src.api.routes.v1.meals_manual_text.resolve_or_conflict",
            new=AsyncMock(return_value=stored),
        ),
        patch(
            "src.api.routes.v1.meals_manual_text.manual_meal_fingerprint",
            return_value="abc",
        ),
    ):
        response = await create_manual_meal(
            request=SimpleNamespace(),
            payload=_payload(),
            user_id="user-1",
            event_bus=AsyncMock(),
            cache_service=None,
            task_manager=None,
            ai_manager=AsyncMock(),
            idempotency_key_header="op-1",
        )
    assert response.meal_id == "meal-1"


@pytest.mark.asyncio
async def test_manual_meal_conflict_returns_409():
    from src.infra.services.durable_write_service import DurableWriteConflictError

    with (
        patch(
            "src.api.routes.v1.meals_manual_text.resolve_or_conflict",
            new=AsyncMock(side_effect=DurableWriteConflictError),
        ),
        patch(
            "src.api.routes.v1.meals_manual_text.manual_meal_fingerprint",
            return_value="abc",
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await create_manual_meal(
                request=SimpleNamespace(),
                payload=_payload(),
                user_id="user-1",
                event_bus=AsyncMock(),
                cache_service=None,
                task_manager=None,
                ai_manager=AsyncMock(),
                idempotency_key_header="op-1",
            )
    assert exc.value.status_code == 409
    assert exc.value.detail["error_code"] == "IDEMPOTENCY_KEY_CONFLICT"


@pytest.mark.asyncio
async def test_manual_meal_persists_durable_write_on_first_create():
    meal = SimpleNamespace(
        meal_id="meal-new",
        created_at=datetime(2026, 8, 11, tzinfo=UTC),
    )
    event_bus = AsyncMock()
    event_bus.send = AsyncMock(return_value=meal)
    save = AsyncMock()
    with (
        patch(
            "src.api.routes.v1.meals_manual_text.resolve_or_conflict",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "src.api.routes.v1.meals_manual_text.manual_meal_fingerprint",
            return_value="fp-1",
        ),
        patch(
            "src.api.routes.v1.meals_manual_text.save_durable_write",
            new=save,
        ),
        patch(
            "src.api.routes.v1.meals_manual_text.schedule_value_insight_generation",
        ),
        patch(
            "src.api.routes.v1.meals_manual_text.MealMapper.to_detailed_response",
            return_value=None,
        ),
        patch(
            "src.api.routes.v1.meals_manual_text.get_request_language",
            return_value="en",
        ),
    ):
        response = await create_manual_meal(
            request=SimpleNamespace(),
            payload=_payload(),
            user_id="user-1",
            event_bus=event_bus,
            cache_service=None,
            task_manager=None,
            ai_manager=AsyncMock(),
            idempotency_key_header="op-2",
        )
    assert response.meal_id == "meal-new"
    save.assert_awaited_once()
    assert save.await_args.kwargs["idempotency_key"] == "op-2"
    assert save.await_args.kwargs["request_fingerprint"] == "fp-1"

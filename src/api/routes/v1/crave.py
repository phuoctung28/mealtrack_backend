from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.schemas.request.crave_requests import RecordSwipesIn
from src.api.schemas.response.crave_responses import CraveDeckResponse
from src.app.commands.crave.record_swipes_command import RecordSwipesCommand, SwipeItem
from src.app.queries.crave.get_crave_deck_query import GetCraveDeckQuery
from src.app.queries.crave.get_crave_recipe_query import GetCraveRecipeQuery
from src.app.queries.saved_suggestion import GetSavedSuggestionsQuery
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/crave", tags=["Crave"])


@router.get("/deck", response_model=CraveDeckResponse)
async def get_deck(
    meal_type: str = Query(..., min_length=1, max_length=20),
    deck_size: int = Query(15, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        return await event_bus.send(
            GetCraveDeckQuery(
                user_id=user_id,
                meal_type=meal_type,
                deck_size=deck_size,
                is_paid=True,
            )
        )
    except Exception as exc:
        raise handle_exception(exc) from exc


@router.post("/swipes", status_code=status.HTTP_202_ACCEPTED)
async def record_swipes(
    body: RecordSwipesIn,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        await event_bus.send(
            RecordSwipesCommand(
                user_id=user_id,
                deck_id=body.deck_id,
                swipes=[SwipeItem(**swipe.model_dump()) for swipe in body.swipes],
            )
        )
        return {"status": "accepted"}
    except Exception as exc:
        raise handle_exception(exc) from exc


@router.get("/meals/{meal_id}/recipe")
async def get_recipe(
    meal_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        return await event_bus.send(GetCraveRecipeQuery(catalog_meal_id=meal_id))
    except Exception as exc:
        raise handle_exception(exc) from exc


@router.get("/my-picks")
async def my_picks(
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        return await event_bus.send(GetSavedSuggestionsQuery(user_id=user_id))
    except Exception as exc:
        raise handle_exception(exc) from exc

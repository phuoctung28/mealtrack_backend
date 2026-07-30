"""
TDEE calculation API endpoints - Preview and calculation without authentication.
"""

from fastapi import APIRouter, Depends, Request
from slowapi.util import get_remote_address

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.middleware.rate_limit import limiter
from src.api.schemas.request import TdeeCalculationRequest
from src.api.schemas.response import MacroTargetsResponse, TdeeCalculationResponse
from src.app.queries.tdee import PreviewTdeeQuery
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/tdee", tags=["TDEE"])


@router.post("/preview", response_model=TdeeCalculationResponse)
@limiter.limit("10/minute", key_func=get_remote_address)
async def preview_tdee(
    request: Request,
    payload: TdeeCalculationRequest,
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Preview TDEE calculation without authentication.

    Used by mobile onboarding to show consistent macro targets
    before user creates account. No data is persisted.

    No authentication required.
    """
    event_bus = get_configured_event_bus()

    query = PreviewTdeeQuery(
        age=payload.age,
        sex=payload.sex.value,
        height=payload.height,
        weight=payload.weight,
        job_type=payload.job_type.value,
        training_days_per_week=payload.training_days_per_week,
        training_minutes_per_session=payload.training_minutes_per_session,
        goal=payload.goal.value,
        body_fat_percentage=payload.body_fat_percentage,
        unit_system=payload.unit_system.value,
        training_level=(
            payload.training_level.value if payload.training_level else None
        ),
        diet_type=payload.diet_type.value,
        custom_protein_g=payload.custom_protein_g,
        custom_carbs_g=payload.custom_carbs_g,
        custom_fat_g=payload.custom_fat_g,
        requested_calories=payload.requested_calories,
    )

    result = await event_bus.send(query)

    return TdeeCalculationResponse(
        calculation_contract=result["calculation_contract"],
        bmr=result["bmr"],
        tdee=result["tdee"],
        macros=MacroTargetsResponse(
            calories=result["macros"]["calories"],
            protein=result["macros"]["protein"],
            carbs=result["macros"]["carbs"],
            fat=result["macros"]["fat"],
        ),
        goal=payload.goal,
        activity_multiplier=result["activity_multiplier"],
        formula_used=result["formula_used"],
        is_custom=result["is_custom"],
        macro_preset=result["macro_preset"],
    )

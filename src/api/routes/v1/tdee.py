"""
TDEE calculation API endpoints - Preview and calculation without authentication.
"""

from fastapi import APIRouter, Depends

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.schemas.request import TdeeCalculationRequest
from src.api.schemas.response import TdeeCalculationResponse, MacroTargetsResponse
from src.app.queries.tdee import PreviewTdeeQuery
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/tdee", tags=["TDEE"])


@router.post("/preview", response_model=TdeeCalculationResponse)
async def preview_tdee(
    request: TdeeCalculationRequest,
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Preview TDEE calculation without authentication.

    Used by mobile onboarding to show consistent macro targets
    before user creates account. No data is persisted.

    No authentication required.
    """
    try:
        from src.api.dependencies.event_bus import get_configured_event_bus

        event_bus = get_configured_event_bus()

        query = PreviewTdeeQuery(
            age=request.age,
            sex=request.sex.value,
            height=request.height,
            weight=request.weight,
            job_type=request.job_type.value,
            training_days_per_week=request.training_days_per_week,
            training_minutes_per_session=request.training_minutes_per_session,
            goal=request.goal.value,
            body_fat_percentage=request.body_fat_percentage,
            unit_system=request.unit_system.value,
            training_level=(
                request.training_level.value if request.training_level else None
            ),
        )

        result = await event_bus.send(query)

        return TdeeCalculationResponse(
            bmr=result["bmr"],
            tdee=result["tdee"],
            macros=MacroTargetsResponse(
                calories=result["macros"]["calories"],
                protein=result["macros"]["protein"],
                carbs=result["macros"]["carbs"],
                fat=result["macros"]["fat"],
            ),
            goal=request.goal,
            activity_multiplier=result["activity_multiplier"],
            formula_used=result["formula_used"],
        )

    except Exception as e:
        raise handle_exception(e) from e

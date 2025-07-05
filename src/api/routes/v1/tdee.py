"""
TDEE API endpoints - Event-driven architecture.
"""
from fastapi import APIRouter, Depends

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.mappers.tdee_mapper import TdeeMapper
from src.api.schemas.request import TdeeCalculationRequest
from src.api.schemas.response import (
    TdeeCalculationResponse
)
from src.app.commands.tdee import (
    CalculateTdeeCommand
)
from src.infra.event_bus import EventBus

router = APIRouter(prefix="", tags=["tdee"])


@router.post("/tdee", response_model=TdeeCalculationResponse)
async def calculate_tdee(
    request: TdeeCalculationRequest,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Calculate BMR, TDEE, and macro targets.
    
    Features:
    - Mifflin-St Jeor formula (without body fat %)
    - Katch-McArdle formula (with body fat %)
    - Supports metric (kg/cm) and imperial (lbs/inches)
    - Returns macro targets for maintenance/cutting/bulking
    """
    try:
        # Create command
        command = CalculateTdeeCommand(
            age=request.age,
            sex=request.sex,
            height_cm=request.height,
            weight_kg=request.weight,
            activity_level=request.activity_level,
            goal=request.goal,
            body_fat_percentage=request.body_fat_percentage,
            unit_system=request.unit_system
        )
        
        # Send command
        result = await event_bus.send(command)
        
        # Create a domain response object for the mapper
        from src.domain.model.tdee import TdeeResponse, Macros, Goal
        from src.domain.model.macros import Macros as DomainMacros
        
        # Map goal string to enum
        goal_map = {
            'maintenance': Goal.MAINTENANCE,
            'cutting': Goal.CUTTING,
            'bulking': Goal.BULKING
        }
        
        # Create domain response
        domain_response = TdeeResponse(
            bmr=result["bmr"],
            tdee=result["tdee"],
            macros=DomainMacros(
                protein=result["macros"]["protein"],
                carbs=result["macros"]["carbs"],
                fat=result["macros"]["fat"]
            ),
            goal=goal_map[request.goal],
            activity_multiplier=result.get("activity_multiplier", 1.2),
            formula_used=result.get("formula_used", "Mifflin-St Jeor")
        )
        
        # Use mapper to convert to response DTO
        mapper = TdeeMapper()
        return mapper.to_response_dto(domain_response)
        
    except Exception as e:
        raise handle_exception(e)
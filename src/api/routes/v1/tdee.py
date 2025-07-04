import logging

from fastapi import APIRouter, HTTPException, status, Depends

from src.api.dependencies import get_tdee_handler
from src.api.mappers.tdee_mapper import TdeeMapper
from src.api.schemas.request import TdeeCalculationRequest
from src.api.schemas.response import TdeeCalculationResponse
from src.app.handlers.tdee_handler import TdeeHandler

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["tdee"],
)


@router.post("/tdee", status_code=status.HTTP_200_OK, response_model=TdeeCalculationResponse)
async def calculate_tdee(
    request: TdeeCalculationRequest,
    handler: TdeeHandler = Depends(get_tdee_handler)
):
    """
    Calculate BMR, TDEE, and macro targets based on Flutter onboarding data.
    
    This endpoint supports both metric and imperial units and returns data
    in the format expected by Flutter TdeeResult class:
    - Uses Mifflin-St Jeor formula when body_fat_percentage is absent
    - Uses Katch-McArdle formula when body_fat_percentage is present
    - Returns BMR, TDEE, and macro targets for maintenance/cutting/bulking goals
    - Supports both metric (kg/cm) and imperial (lbs/inches) unit systems
    """
    try:
        # Initialize mapper
        mapper = TdeeMapper()
        
        # Convert request DTO to domain model
        domain_request = mapper.to_domain(request)
        
        # Delegate to application layer handler
        result = await handler.calculate_tdee(
            age=domain_request.age,
            sex=domain_request.sex.value,
            height=domain_request.height,
            weight=domain_request.weight,
            body_fat_percentage=domain_request.body_fat_pct,
            activity_level=domain_request.activity_level.value,
            goal=domain_request.goal.value,
            unit_system=domain_request.unit_system.value
        )
        
        logger.info(f"TDEE calculation successful: BMR={result.bmr}, TDEE={result.tdee} ({request.unit_system})")
        
        # Convert domain response to API response DTO
        return mapper.to_response_dto(result)
        
    except ValueError as e:
        logger.warning(f"Validation error in TDEE calculation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error calculating TDEE: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during TDEE calculation"
        ) 
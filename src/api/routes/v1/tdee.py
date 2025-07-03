import logging
from fastapi import APIRouter, HTTPException, status, Depends

from src.api.dependencies import get_tdee_handler
from src.api.schemas.tdee_schemas import TdeeCalculationRequest, TdeeCalculationResponse
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
        # Delegate to application layer handler
        result = await handler.calculate_tdee(
            age=request.age,
            sex=request.sex,
            height=request.height,
            weight=request.weight,
            body_fat_percentage=request.body_fat_percentage,
            activity_level=request.activity_level,
            goal=request.goal,
            unit_system=request.unit_system
        )
        
        # Convert domain response to API response format
        response_dict = result.to_dict()
        
        logger.info(f"TDEE calculation successful: BMR={result.bmr}, TDEE={result.tdee} ({request.unit_system})")
        
        return TdeeCalculationResponse(**response_dict)
        
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
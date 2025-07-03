import logging
from typing import Optional

from src.domain.model.tdee import TdeeRequest, TdeeResponse, Sex, ActivityLevel, Goal, UnitSystem
from src.domain.services.tdee_service import TdeeCalculationService

logger = logging.getLogger(__name__)


class TdeeHandler:
    """Application layer handler for TDEE calculations."""
    
    def __init__(self, tdee_service: TdeeCalculationService):
        self.tdee_service = tdee_service
    
    async def calculate_tdee(
        self,
        age: int,
        sex: str,
        height: float,
        weight: float,
        body_fat_percentage: Optional[float],
        activity_level: str,
        goal: str,
        unit_system: str = "metric"
    ) -> TdeeResponse:
        """Handle TDEE calculation request."""
        try:
            # Convert API strings to domain enums
            sex_enum = Sex(sex.lower())
            activity_enum = ActivityLevel(activity_level.lower())
            goal_enum = Goal(goal.lower())
            unit_system_enum = UnitSystem(unit_system.lower())
            
            # Create domain request object
            request = TdeeRequest(
                age=age,
                sex=sex_enum,
                height=height,
                weight=weight,
                body_fat_pct=body_fat_percentage,
                activity_level=activity_enum,
                goal=goal_enum,
                unit_system=unit_system_enum
            )
            
            # Delegate to domain service
            result = self.tdee_service.calculate_tdee(request)
            logger.info(f"Calculated TDEE: BMR={result.bmr}, TDEE={result.tdee} for {sex} age {age} ({unit_system})")
            
            return result
            
        except ValueError as e:
            logger.error(f"Validation error in TDEE calculation: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error calculating TDEE: {str(e)}", exc_info=True)
            raise 
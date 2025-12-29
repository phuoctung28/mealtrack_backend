"""
Mapper for TDEE calculation DTOs and domain models.
"""
from src.api.mappers.base_mapper import BaseMapper
from src.api.schemas.request import TdeeCalculationRequest
from src.api.schemas.response import (
    TdeeCalculationResponse,
    MacroTargetsResponse
)
from src.domain.model.user import (
    TdeeRequest,
    TdeeResponse,
    Sex,
    ActivityLevel,
    Goal,
    UnitSystem
)


class TdeeMapper(BaseMapper[TdeeRequest, TdeeCalculationRequest, TdeeCalculationResponse]):
    """Mapper for TDEE calculation data transformation."""
    
    def to_domain(self, dto: TdeeCalculationRequest) -> TdeeRequest:
        """
        Convert TdeeCalculationRequest DTO to TdeeRequest domain model.
        
        Args:
            dto: TDEE calculation request DTO
            
        Returns:
            TdeeRequest domain model
        """
        # Map string values to enums
        sex_map = {
            'male': Sex.MALE,
            'female': Sex.FEMALE
        }
        
        activity_map = {
            'sedentary': ActivityLevel.SEDENTARY,
            'light': ActivityLevel.LIGHT,
            'moderate': ActivityLevel.MODERATE,
            'active': ActivityLevel.ACTIVE,
            'extra': ActivityLevel.EXTRA
        }
        
        goal_map = {
            'maintenance': Goal.MAINTENANCE,
            'cutting': Goal.CUTTING,
            'bulking': Goal.BULKING,
            'recomp': Goal.RECOMP
        }
        
        unit_map = {
            'metric': UnitSystem.METRIC,
            'imperial': UnitSystem.IMPERIAL
        }
        
        return TdeeRequest(
            age=dto.age,
            sex=sex_map[dto.sex],
            height=dto.height,
            weight=dto.weight,
            body_fat_pct=dto.body_fat_percentage,
            activity_level=activity_map[dto.activity_level],
            goal=goal_map[dto.goal],
            unit_system=unit_map[dto.unit_system]
        )
    
    def to_response_dto(self, domain: TdeeResponse) -> TdeeCalculationResponse:
        """
        Convert TdeeResponse domain model to TdeeCalculationResponse DTO.
        
        Args:
            domain: TDEE response domain model
            
        Returns:
            TdeeCalculationResponse DTO
        """
        # Convert macro targets
        macros_dto = MacroTargetsResponse(
            calories=domain.macros.calories,
            protein=domain.macros.protein,
            fat=domain.macros.fat,
            carbs=domain.macros.carbs
        )
        
        return TdeeCalculationResponse(
            bmr=domain.bmr,
            tdee=domain.tdee,
            macros=macros_dto,
            goal=domain.goal.value  # Convert enum to string
        )
    
    @staticmethod
    def map_to_profile_dict(dto: TdeeCalculationRequest) -> dict:
        """
        Convert TdeeCalculationRequest to profile dictionary for database.
        
        Args:
            dto: TDEE calculation request DTO
            
        Returns:
            Dictionary suitable for UserProfile creation
        """
        return {
            "age": dto.age,
            "gender": dto.sex,
            "height_cm": dto.height if dto.unit_system == "metric" else dto.height * 2.54,
            "weight_kg": dto.weight if dto.unit_system == "metric" else dto.weight * 0.453592,
            "body_fat_percentage": dto.body_fat_percentage
        }

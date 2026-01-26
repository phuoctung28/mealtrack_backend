"""
Mapper for TDEE calculation DTOs and domain models.
"""
from src.api.mappers.base_mapper import BaseMapper
from src.api.schemas.request import TdeeCalculationRequest
from src.api.schemas.response import (
    TdeeCalculationResponse,
    MacroTargetsResponse
)
from src.domain.mappers.activity_goal_mapper import ActivityGoalMapper
from src.domain.model.user import (
    TdeeRequest,
    TdeeResponse,
    Sex,
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
        # Map string values to enums using centralized mapper
        sex = Sex.MALE if dto.sex.lower() == 'male' else Sex.FEMALE

        return TdeeRequest(
            age=dto.age,
            sex=sex,
            height=dto.height,
            weight=dto.weight,
            body_fat_pct=dto.body_fat_percentage,
            activity_level=ActivityGoalMapper.map_activity_level(dto.activity_level.value),
            goal=ActivityGoalMapper.map_goal(dto.goal.value),
            unit_system=UnitSystem.METRIC if dto.unit_system.value == 'metric' else UnitSystem.IMPERIAL
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

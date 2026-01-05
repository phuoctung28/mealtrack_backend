"""
Unit tests for TDEE mapper.
"""
import pytest

from src.api.mappers.tdee_mapper import TdeeMapper
from src.api.schemas.request import TdeeCalculationRequest
from src.domain.model.user import TdeeResponse, MacroTargets


class TestTdeeMapper:
    """Test TdeeMapper methods."""

    def setup_method(self):
        """Set up test mapper."""
        self.mapper = TdeeMapper()

    def test_to_domain_male_sedentary_maintenance_metric(self):
        """Test converting DTO to domain model - male, sedentary, maintenance, metric."""
        dto = TdeeCalculationRequest(
            age=30,
            sex="male",
            height=175,
            weight=70,
            body_fat_percentage=15.0,
            activity_level="sedentary",
            goal="maintenance",
            unit_system="metric"
        )
        
        domain = self.mapper.to_domain(dto)
        
        assert domain.age == 30
        assert domain.sex.value == "male"
        assert domain.height == 175
        assert domain.weight == 70
        assert domain.body_fat_pct == 15.0
        assert domain.activity_level.value == "sedentary"
        assert domain.goal.value == "recomp"
        assert domain.unit_system.value == "metric"

    def test_to_domain_female_light_cutting_imperial(self):
        """Test converting DTO to domain model - female, light, cutting, imperial."""
        dto = TdeeCalculationRequest(
            age=25,
            sex="female",
            height=65,  # inches
            weight=140,  # pounds
            body_fat_percentage=20.0,
            activity_level="light",
            goal="cut",
            unit_system="imperial"
        )
        
        domain = self.mapper.to_domain(dto)
        
        assert domain.sex.value == "female"
        assert domain.activity_level.value == "light"
        assert domain.goal.value == "cutting"
        assert domain.unit_system.value == "imperial"

    def test_to_domain_all_activity_levels(self):
        """Test converting DTO with all activity levels."""
        activity_levels = ["sedentary", "light", "moderate", "active", "extra"]
        
        for activity in activity_levels:
            dto = TdeeCalculationRequest(
                age=30,
                sex="male",
                height=175,
                weight=70,
                body_fat_percentage=None,
                activity_level=activity,
                goal="recomp",
                unit_system="metric"
            )
            
            domain = self.mapper.to_domain(dto)
            assert domain.activity_level.value == activity

    def test_to_domain_all_goals(self):
        """Test converting DTO with all goals."""
        goals = ["cut", "bulk", "recomp"]
        
        for goal in goals:
            dto = TdeeCalculationRequest(
                age=30,
                sex="male",
                height=175,
                weight=70,
                body_fat_percentage=None,
                activity_level="moderate",
                goal=goal,
                unit_system="metric"
            )
            
            domain = self.mapper.to_domain(dto)
            assert domain.goal.value == goal

    def test_to_response_dto(self):
        """Test converting domain model to response DTO."""
        from src.domain.model.user import Goal
        
        domain = TdeeResponse(
            bmr=1700.0,
            tdee=2200.0,
            macros=MacroTargets(calories=2200, protein=165, carbs=220, fat=73),
            goal=Goal.RECOMP
        )
        
        dto = self.mapper.to_response_dto(domain)
        
        assert dto.bmr == 1700.0
        assert dto.tdee == 2200.0
        assert dto.macros.calories == 2200
        assert dto.macros.protein == 165
        assert dto.macros.carbs == 220
        assert dto.macros.fat == 73
        assert dto.goal == "recomp"

    def test_map_to_profile_dict_metric(self):
        """Test mapping to profile dict with metric units."""
        dto = TdeeCalculationRequest(
            age=30,
            sex="male",
            height=175,
            weight=70,
            body_fat_percentage=15.0,
            activity_level="moderate",
            goal="maintenance",
            unit_system="metric"
        )
        
        profile_dict = TdeeMapper.map_to_profile_dict(dto)
        
        assert profile_dict["age"] == 30
        assert profile_dict["gender"] == "male"
        assert profile_dict["height_cm"] == 175
        assert profile_dict["weight_kg"] == 70
        assert profile_dict["body_fat_percentage"] == 15.0

    def test_map_to_profile_dict_imperial(self):
        """Test mapping to profile dict with imperial units."""
        dto = TdeeCalculationRequest(
            age=30,
            sex="male",
            height=70,  # inches
            weight=154,  # pounds
            body_fat_percentage=15.0,
            activity_level="moderate",
            goal="maintenance",
            unit_system="imperial"
        )
        
        profile_dict = TdeeMapper.map_to_profile_dict(dto)
        
        assert profile_dict["age"] == 30
        assert profile_dict["gender"] == "male"
        # 70 inches * 2.54 = 177.8 cm
        assert abs(profile_dict["height_cm"] - 177.8) < 0.1
        # 154 pounds * 0.453592 = 69.85 kg
        assert abs(profile_dict["weight_kg"] - 69.85) < 0.1
        assert profile_dict["body_fat_percentage"] == 15.0


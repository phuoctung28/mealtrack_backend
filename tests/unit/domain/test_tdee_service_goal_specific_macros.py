"""
Unit tests for TDEE service goal-specific macro calculations.

Tests the refactored _calculate_all_macro_targets method to verify:
1. Goal-specific calorie adjustments (surplus/deficit)
2. Goal-specific macro ratios
3. Correct macro calculations with proper rounding
"""
import pytest

from src.domain.model.user import (
    TdeeRequest,
    MacroTargets,
    Sex,
    ActivityLevel,
    Goal,
    UnitSystem
)
from src.domain.services.tdee_service import TdeeCalculationService
from src.domain.constants import TDEEConstants


class TestTdeeServiceGoalSpecificMacros:
    """Test goal-specific macro calculations in TdeeCalculationService."""

    @pytest.fixture
    def service(self):
        """Provide TdeeCalculationService instance."""
        return TdeeCalculationService()

    @pytest.fixture
    def base_request(self):
        """Provide base TDEE request for testing."""
        # 30-year-old male, 80kg, 180cm, moderate activity level
        return TdeeRequest(
            age=30,
            sex=Sex.MALE,
            height=180,
            weight=80,
            body_fat_pct=None,
            activity_level=ActivityLevel.MODERATE,
            goal=Goal.RECOMP,
            unit_system=UnitSystem.METRIC
        )

    @pytest.fixture
    def base_tdee(self):
        """Calculate base TDEE for test case."""
        # 30-year-old male, 80kg, 180cm, moderate activity
        # Mifflin-St Jeor: 10*80 + 6.25*180 - 5*30 + 5 = 800 + 1125 - 150 + 5 = 1780
        # TDEE with moderate (1.55): 1780 * 1.55 = 2759
        return 2759.0

    # ===== BULKING TESTS =====

    def test_bulking_uses_300_calorie_surplus(self, service, base_request):
        """Verify bulking goal applies 300 calorie surplus to TDEE."""
        base_request.goal = Goal.BULK
        response = service.calculate_tdee(base_request)

        # Expected: TDEE + 300 = 2759 + 300 = 3059
        expected_calories = 2759.0 + 300
        assert response.macros.calories == pytest.approx(expected_calories, abs=0.1)

    def test_bulking_macro_ratios(self, service, base_request):
        """Verify bulking uses 30% protein, 45% carbs, 25% fat ratios."""
        base_request.goal = Goal.BULK
        response = service.calculate_tdee(base_request)

        calories = response.macros.calories

        # Expected macros from ratios
        expected_protein = (calories * 0.30) / 4
        expected_carbs = (calories * 0.45) / 4
        expected_fat = (calories * 0.25) / 9

        # Allow ±1g tolerance for rounding
        assert response.macros.protein == pytest.approx(expected_protein, abs=1)
        assert response.macros.carbs == pytest.approx(expected_carbs, abs=1)
        assert response.macros.fat == pytest.approx(expected_fat, abs=1)

    def test_bulking_macro_ratios_percentage(self, service, base_request):
        """Verify bulking macro percentages sum correctly."""
        base_request.goal = Goal.BULK
        response = service.calculate_tdee(base_request)

        calories = response.macros.calories

        # Verify calorie composition
        protein_cals = response.macros.protein * 4
        carbs_cals = response.macros.carbs * 4
        fat_cals = response.macros.fat * 9

        total_cals = protein_cals + carbs_cals + fat_cals

        # Should be approximately equal to target calories
        assert total_cals == pytest.approx(calories, rel=0.02)

    # ===== CUTTING TESTS =====

    def test_cutting_uses_500_calorie_deficit(self, service, base_request):
        """Verify cutting goal applies 500 calorie deficit to TDEE."""
        base_request.goal = Goal.CUT
        response = service.calculate_tdee(base_request)

        # Expected: TDEE - 500 = 2759 - 500 = 2259
        expected_calories = 2759.0 - 500
        assert response.macros.calories == pytest.approx(expected_calories, abs=0.1)

    def test_cutting_macro_ratios(self, service, base_request):
        """Verify cutting uses 35% protein, 40% carbs, 25% fat ratios."""
        base_request.goal = Goal.CUT
        response = service.calculate_tdee(base_request)

        calories = response.macros.calories

        # Expected macros from ratios
        expected_protein = (calories * 0.35) / 4
        expected_carbs = (calories * 0.40) / 4
        expected_fat = (calories * 0.25) / 9

        # Allow ±1g tolerance for rounding
        assert response.macros.protein == pytest.approx(expected_protein, abs=1)
        assert response.macros.carbs == pytest.approx(expected_carbs, abs=1)
        assert response.macros.fat == pytest.approx(expected_fat, abs=1)

    def test_cutting_macro_ratios_percentage(self, service, base_request):
        """Verify cutting macro percentages sum correctly."""
        base_request.goal = Goal.CUT
        response = service.calculate_tdee(base_request)

        calories = response.macros.calories

        # Verify calorie composition
        protein_cals = response.macros.protein * 4
        carbs_cals = response.macros.carbs * 4
        fat_cals = response.macros.fat * 9

        total_cals = protein_cals + carbs_cals + fat_cals

        # Should be approximately equal to target calories
        assert total_cals == pytest.approx(calories, rel=0.02)


    # ===== RECOMP TESTS =====

    def test_recomp_uses_tdee(self, service, base_request):
        """Verify recomposition goal uses TDEE without adjustment."""
        base_request.goal = Goal.RECOMP
        response = service.calculate_tdee(base_request)

        # Expected: TDEE = 2759 (no adjustment)
        expected_calories = 2759.0
        assert response.macros.calories == pytest.approx(expected_calories, abs=0.1)

    def test_recomp_macro_ratios(self, service, base_request):
        """Verify recomposition uses 35% protein, 40% carbs, 25% fat ratios."""
        base_request.goal = Goal.RECOMP
        response = service.calculate_tdee(base_request)

        calories = response.macros.calories

        # Expected macros from ratios
        expected_protein = (calories * 0.35) / 4
        expected_carbs = (calories * 0.40) / 4
        expected_fat = (calories * 0.25) / 9

        # Allow ±1g tolerance for rounding
        assert response.macros.protein == pytest.approx(expected_protein, abs=1)
        assert response.macros.carbs == pytest.approx(expected_carbs, abs=1)
        assert response.macros.fat == pytest.approx(expected_fat, abs=1)

    def test_recomp_macro_ratios_percentage(self, service, base_request):
        """Verify recomposition macro percentages sum correctly."""
        base_request.goal = Goal.RECOMP
        response = service.calculate_tdee(base_request)

        calories = response.macros.calories

        # Verify calorie composition
        protein_cals = response.macros.protein * 4
        carbs_cals = response.macros.carbs * 4
        fat_cals = response.macros.fat * 9

        total_cals = protein_cals + carbs_cals + fat_cals

        # Should be approximately equal to target calories
        assert total_cals == pytest.approx(calories, rel=0.02)

    # ===== GOAL ENUM TESTS =====

    def test_goal_enum_has_recomp(self):
        """Verify Goal enum contains RECOMP value."""
        assert hasattr(Goal, 'RECOMP')
        assert Goal.RECOMP.value == "recomp"

    def test_goal_enum_has_all_required_goals(self):
        """Verify Goal enum has all required goal types."""
        required_goals = {'CUT', 'BULK', 'RECOMP'}
        available_goals = {g.name for g in Goal}
        assert required_goals.issubset(available_goals)

    # ===== MACRO TARGETS OBJECT TESTS =====

    def test_macro_targets_has_required_fields(self, service, base_request):
        """Verify MacroTargets object has calories, protein, fat, carbs fields."""
        response = service.calculate_tdee(base_request)
        macro_targets = response.macros

        # Verify all required fields exist and are floats
        assert hasattr(macro_targets, 'calories')
        assert hasattr(macro_targets, 'protein')
        assert hasattr(macro_targets, 'fat')
        assert hasattr(macro_targets, 'carbs')

        assert isinstance(macro_targets.calories, (int, float))
        assert isinstance(macro_targets.protein, (int, float))
        assert isinstance(macro_targets.fat, (int, float))
        assert isinstance(macro_targets.carbs, (int, float))

    def test_macro_targets_values_are_positive(self, service, base_request):
        """Verify all macro target values are positive."""
        response = service.calculate_tdee(base_request)
        macro_targets = response.macros

        assert macro_targets.calories > 0
        assert macro_targets.protein > 0
        assert macro_targets.fat > 0
        assert macro_targets.carbs > 0

    # ===== CROSS-GOAL COMPARISON TESTS =====

    def test_bulking_calories_higher_than_recomp(self, service, base_request):
        """Verify bulking has higher calories than recomposition."""
        base_request.goal = Goal.BULK
        bulking = service.calculate_tdee(base_request)

        base_request.goal = Goal.RECOMP
        recomp = service.calculate_tdee(base_request)

        assert bulking.macros.calories > recomp.macros.calories
        assert bulking.macros.calories == pytest.approx(
            recomp.macros.calories + 300, abs=0.1
        )

    def test_cutting_calories_lower_than_recomp(self, service, base_request):
        """Verify cutting has lower calories than recomposition."""
        base_request.goal = Goal.CUT
        cutting = service.calculate_tdee(base_request)

        base_request.goal = Goal.RECOMP
        recomp = service.calculate_tdee(base_request)

        assert cutting.macros.calories < recomp.macros.calories
        assert cutting.macros.calories == pytest.approx(
            recomp.macros.calories - 500, abs=0.1
        )

    def test_recomp_calories_equal_tdee(self, service, base_request):
        """Verify recomposition calories equal TDEE (no calorie adjustment)."""
        # Calculate TDEE independently
        tdee_service = service
        base_request.goal = Goal.RECOMP
        response = tdee_service.calculate_tdee(base_request)

        # Recomp should have no calorie adjustment (calories = TDEE)
        # TDEE was already calculated and set in response
        # Just verify that recomp adjustment is 0
        assert response.macros.calories == pytest.approx(response.tdee, abs=0.1)

    def test_cutting_higher_protein_than_bulking(self, service, base_request):
        """Verify cutting has higher protein ratio than bulking."""
        base_request.goal = Goal.CUT
        cutting = service.calculate_tdee(base_request)
        cutting_protein_ratio = cutting.macros.protein * 4 / cutting.macros.calories

        base_request.goal = Goal.BULK
        bulking = service.calculate_tdee(base_request)
        bulking_protein_ratio = bulking.macros.protein * 4 / bulking.macros.calories

        # Cutting: 35%, Bulking: 30%
        assert cutting_protein_ratio > bulking_protein_ratio
        assert cutting_protein_ratio == pytest.approx(0.35, abs=0.01)
        assert bulking_protein_ratio == pytest.approx(0.30, abs=0.01)

    def test_bulking_higher_carbs_than_cutting(self, service, base_request):
        """Verify bulking has higher carb ratio than cutting."""
        base_request.goal = Goal.BULK
        bulking = service.calculate_tdee(base_request)
        bulking_carb_ratio = bulking.macros.carbs * 4 / bulking.macros.calories

        base_request.goal = Goal.CUT
        cutting = service.calculate_tdee(base_request)
        cutting_carb_ratio = cutting.macros.carbs * 4 / cutting.macros.calories

        # Bulking: 45%, Cutting: 40%
        assert bulking_carb_ratio > cutting_carb_ratio
        assert bulking_carb_ratio == pytest.approx(0.45, abs=0.01)
        assert cutting_carb_ratio == pytest.approx(0.40, abs=0.01)

    # ===== CONSTANTS VALIDATION TESTS =====

    def test_tdee_constants_have_goal_adjustments(self):
        """Verify TDEEConstants defines goal adjustments."""
        assert hasattr(TDEEConstants, 'CUTTING_DEFICIT')
        assert hasattr(TDEEConstants, 'BULKING_SURPLUS')
        assert hasattr(TDEEConstants, 'RECOMP_ADJUSTMENT')

        assert TDEEConstants.CUTTING_DEFICIT == 500
        assert TDEEConstants.BULKING_SURPLUS == 300
        assert TDEEConstants.RECOMP_ADJUSTMENT == 0

    def test_tdee_constants_have_macro_ratios(self):
        """Verify TDEEConstants defines macro ratios for all goals."""
        assert hasattr(TDEEConstants, 'MACRO_RATIOS')

        required_goals = {'bulk', 'cut', 'recomp'}
        available_goals = set(TDEEConstants.MACRO_RATIOS.keys())

        assert required_goals.issubset(available_goals)

    def test_macro_ratios_sum_to_one(self):
        """Verify each goal's macro ratios sum to 1.0."""
        for goal_name, ratios in TDEEConstants.MACRO_RATIOS.items():
            total = ratios['protein'] + ratios['carbs'] + ratios['fat']
            assert total == pytest.approx(1.0, abs=0.001), \
                f"Goal {goal_name} ratios don't sum to 1.0: {total}"

    # ===== DIFFERENT ACTIVITY LEVELS TEST =====

    def test_macro_targets_consistent_across_activity_levels(self, service, base_request):
        """Verify macro calculation logic works across different activity levels."""
        activity_levels = [
            ActivityLevel.SEDENTARY,
            ActivityLevel.LIGHT,
            ActivityLevel.MODERATE,
            ActivityLevel.ACTIVE,
            ActivityLevel.EXTRA
        ]

        base_request.goal = Goal.BULK

        for activity in activity_levels:
            base_request.activity_level = activity
            response = service.calculate_tdee(base_request)

            # Verify structure is valid for all activity levels
            assert response.macros.calories > 0
            assert response.macros.protein > 0
            assert response.macros.fat > 0
            assert response.macros.carbs > 0

            # Verify macro ratios are correct
            protein_ratio = response.macros.protein * 4 / response.macros.calories
            assert protein_ratio == pytest.approx(0.30, abs=0.01)

    # ===== DIFFERENT WEIGHTS TEST =====

    def test_macros_scale_with_calories(self, service, base_request):
        """Verify macros scale proportionally with calorie changes."""
        base_request.goal = Goal.BULK
        base_request.weight = 80
        response_80kg = service.calculate_tdee(base_request)

        # Higher weight = higher TDEE = higher calorie target
        base_request.weight = 100
        response_100kg = service.calculate_tdee(base_request)

        # Both should have same macro ratios
        protein_ratio_80 = response_80kg.macros.protein * 4 / response_80kg.macros.calories
        protein_ratio_100 = response_100kg.macros.protein * 4 / response_100kg.macros.calories

        assert protein_ratio_80 == pytest.approx(protein_ratio_100, abs=0.01)
        assert response_100kg.macros.calories > response_80kg.macros.calories

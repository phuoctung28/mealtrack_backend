"""
Unit tests for TDEE service weight-based macro calculations.

Tests the refactored _calculate_all_macro_targets method to verify:
1. Goal-specific calorie adjustments (surplus/deficit)
2. Weight-based protein and fat calculations (g/kg body weight)
3. Carbs calculated as remainder calories
4. Min/max bounds enforcement
"""
import pytest

from src.domain.constants import TDEEConstants
from src.domain.model.user import (
    TdeeRequest,
    Sex,
    ActivityLevel,
    Goal,
    UnitSystem
)
from src.domain.services.tdee_service import TdeeCalculationService


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

    def test_bulking_uses_weight_based_protein(self, service, base_request):
        """Verify bulking protein is calculated from body weight."""
        base_request.goal = Goal.BULK
        response = service.calculate_tdee(base_request)

        # Expected: 80kg * 1.6 g/kg = 128g protein
        expected_protein = 80 * 1.6
        assert response.macros.protein == pytest.approx(expected_protein, abs=1)

    def test_bulking_uses_weight_based_fat(self, service, base_request):
        """Verify bulking fat is calculated from body weight."""
        base_request.goal = Goal.BULK
        response = service.calculate_tdee(base_request)

        # Expected: 80kg * 1.0 g/kg = 80g fat
        expected_fat = 80 * 1.0
        assert response.macros.fat == pytest.approx(expected_fat, abs=1)

    def test_bulking_carbs_calculated_as_remainder(self, service, base_request):
        """Verify bulking carbs are calculated from remaining calories."""
        base_request.goal = Goal.BULK
        response = service.calculate_tdee(base_request)

        calories = response.macros.calories
        protein_cals = response.macros.protein * 4
        fat_cals = response.macros.fat * 9
        expected_carbs = (calories - protein_cals - fat_cals) / 4

        assert response.macros.carbs == pytest.approx(expected_carbs, abs=1)

    # ===== CUTTING TESTS =====

    def test_cutting_uses_500_calorie_deficit(self, service, base_request):
        """Verify cutting goal applies 500 calorie deficit to TDEE."""
        base_request.goal = Goal.CUT
        response = service.calculate_tdee(base_request)

        # Expected: TDEE - 500 = 2759 - 500 = 2259
        expected_calories = 2759.0 - 500
        assert response.macros.calories == pytest.approx(expected_calories, abs=0.1)

    def test_cutting_uses_weight_based_protein(self, service, base_request):
        """Verify cutting protein is calculated from body weight (higher than bulk)."""
        base_request.goal = Goal.CUT
        response = service.calculate_tdee(base_request)

        # Expected: 80kg * 2.0 g/kg = 160g protein (higher to preserve muscle)
        expected_protein = 80 * 2.0
        assert response.macros.protein == pytest.approx(expected_protein, abs=1)

    def test_cutting_uses_weight_based_fat(self, service, base_request):
        """Verify cutting fat is calculated from body weight (lower than bulk)."""
        base_request.goal = Goal.CUT
        response = service.calculate_tdee(base_request)

        # Expected: 80kg * 0.8 g/kg = 64g fat (lower to preserve calories)
        expected_fat = 80 * 0.8
        assert response.macros.fat == pytest.approx(expected_fat, abs=1)

    def test_cutting_carbs_calculated_as_remainder(self, service, base_request):
        """Verify cutting carbs are calculated from remaining calories."""
        base_request.goal = Goal.CUT
        response = service.calculate_tdee(base_request)

        calories = response.macros.calories
        protein_cals = response.macros.protein * 4
        fat_cals = response.macros.fat * 9
        expected_carbs = (calories - protein_cals - fat_cals) / 4

        assert response.macros.carbs == pytest.approx(expected_carbs, abs=1)

    # ===== RECOMP TESTS =====

    def test_recomp_uses_tdee(self, service, base_request):
        """Verify recomposition goal uses TDEE without adjustment."""
        base_request.goal = Goal.RECOMP
        response = service.calculate_tdee(base_request)

        # Expected: TDEE = 2759 (no adjustment)
        expected_calories = 2759.0
        assert response.macros.calories == pytest.approx(expected_calories, abs=0.1)

    def test_recomp_uses_weight_based_protein(self, service, base_request):
        """Verify recomp protein is calculated from body weight."""
        base_request.goal = Goal.RECOMP
        response = service.calculate_tdee(base_request)

        # Expected: 80kg * 1.8 g/kg = 144g protein
        expected_protein = 80 * 1.8
        assert response.macros.protein == pytest.approx(expected_protein, abs=1)

    def test_recomp_uses_weight_based_fat(self, service, base_request):
        """Verify recomp fat is calculated from body weight."""
        base_request.goal = Goal.RECOMP
        response = service.calculate_tdee(base_request)

        # Expected: 80kg * 0.9 g/kg = 72g fat
        expected_fat = 80 * 0.9
        assert response.macros.fat == pytest.approx(expected_fat, abs=1)

    def test_recomp_carbs_calculated_as_remainder(self, service, base_request):
        """Verify recomp carbs are calculated from remaining calories."""
        base_request.goal = Goal.RECOMP
        response = service.calculate_tdee(base_request)

        calories = response.macros.calories
        protein_cals = response.macros.protein * 4
        fat_cals = response.macros.fat * 9
        expected_carbs = (calories - protein_cals - fat_cals) / 4

        assert response.macros.carbs == pytest.approx(expected_carbs, abs=1)

    # ===== EDGE CASE TESTS - CLAMPING =====

    def test_protein_clamped_to_max(self, service, base_request):
        """Verify protein is clamped to MAX_PROTEIN_G for heavy users."""
        base_request.weight = 200  # 200kg * 2.0 = 400g > 300 max
        base_request.goal = Goal.CUT
        response = service.calculate_tdee(base_request)

        assert response.macros.protein == TDEEConstants.MAX_PROTEIN_G

    def test_protein_clamped_to_min(self, service, base_request):
        """Verify protein is clamped to MIN_PROTEIN_G for light users."""
        base_request.weight = 30  # 30kg * 1.6 = 48g < 60 min
        base_request.goal = Goal.BULK
        response = service.calculate_tdee(base_request)

        assert response.macros.protein == TDEEConstants.MIN_PROTEIN_G

    def test_fat_clamped_to_max(self, service, base_request):
        """Verify fat is clamped to MAX_FAT_G for heavy users."""
        base_request.weight = 200  # 200kg * 1.0 = 200g > 150 max
        base_request.goal = Goal.BULK
        response = service.calculate_tdee(base_request)

        assert response.macros.fat == TDEEConstants.MAX_FAT_G

    def test_fat_clamped_to_min(self, service, base_request):
        """Verify fat is clamped to MIN_FAT_G for light users."""
        base_request.weight = 30  # 30kg * 0.8 = 24g < 40 min
        base_request.goal = Goal.CUT
        response = service.calculate_tdee(base_request)

        assert response.macros.fat == TDEEConstants.MIN_FAT_G

    def test_carbs_minimum_50g(self, service, base_request):
        """Verify minimum 50g carbs even when remaining calories are low."""
        # With low TDEE and high weight, carbs could go negative
        # Set up a scenario with low calorie target
        base_request.weight = 80
        base_request.goal = Goal.CUT
        response = service.calculate_tdee(base_request)

        # Carbs should always be at least MIN_CARBS_G
        assert response.macros.carbs >= TDEEConstants.MIN_CARBS_G

    # ===== ORIGINAL PROBLEM CASE TEST =====

    def test_84kg_user_gets_151g_protein_for_recomp(self, service, base_request):
        """Verify 84kg user gets ~151g protein, not 252g (original problem case)."""
        base_request.weight = 84
        base_request.goal = Goal.RECOMP
        response = service.calculate_tdee(base_request)

        # Old calculation: 2880 * 0.35 / 4 = 252g (way too high)
        # New calculation: 84kg * 1.8 g/kg = 151.2g (research-backed)
        expected_protein = 84 * 1.8
        assert response.macros.protein == pytest.approx(expected_protein, abs=1)

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
        base_request.goal = Goal.RECOMP
        response = service.calculate_tdee(base_request)

        # Recomp should have no calorie adjustment (calories = TDEE)
        assert response.macros.calories == pytest.approx(response.tdee, abs=0.1)

    def test_cutting_higher_protein_per_kg_than_bulking(self, service, base_request):
        """Verify cutting uses higher protein per kg than bulking."""
        # Cutting: 2.0 g/kg, Bulking: 1.6 g/kg
        base_request.goal = Goal.CUT
        cutting = service.calculate_tdee(base_request)

        base_request.goal = Goal.BULK
        bulking = service.calculate_tdee(base_request)

        # Both use same weight, so cutting should have more absolute protein
        assert cutting.macros.protein > bulking.macros.protein

    # ===== CONSTANTS VALIDATION TESTS =====

    def test_tdee_constants_have_goal_adjustments(self):
        """Verify TDEEConstants defines goal adjustments."""
        assert hasattr(TDEEConstants, 'CUTTING_DEFICIT')
        assert hasattr(TDEEConstants, 'BULKING_SURPLUS')
        assert hasattr(TDEEConstants, 'RECOMP_ADJUSTMENT')

        assert TDEEConstants.CUTTING_DEFICIT == 500
        assert TDEEConstants.BULKING_SURPLUS == 300
        assert TDEEConstants.RECOMP_ADJUSTMENT == 0

    def test_tdee_constants_have_weight_based_multipliers(self):
        """Verify TDEEConstants defines weight-based multipliers."""
        assert hasattr(TDEEConstants, 'PROTEIN_PER_KG')
        assert hasattr(TDEEConstants, 'FAT_PER_KG')

        required_goals = {'bulk', 'cut', 'recomp'}
        assert required_goals.issubset(set(TDEEConstants.PROTEIN_PER_KG.keys()))
        assert required_goals.issubset(set(TDEEConstants.FAT_PER_KG.keys()))

        # Verify correct values
        assert TDEEConstants.PROTEIN_PER_KG['cut'] == 2.0
        assert TDEEConstants.PROTEIN_PER_KG['recomp'] == 1.8
        assert TDEEConstants.PROTEIN_PER_KG['bulk'] == 1.6
        assert TDEEConstants.FAT_PER_KG['cut'] == 0.8
        assert TDEEConstants.FAT_PER_KG['recomp'] == 0.9
        assert TDEEConstants.FAT_PER_KG['bulk'] == 1.0

    def test_tdee_constants_have_min_max_bounds(self):
        """Verify TDEEConstants defines min/max bounds for macros."""
        assert hasattr(TDEEConstants, 'MIN_PROTEIN_G')
        assert hasattr(TDEEConstants, 'MAX_PROTEIN_G')
        assert hasattr(TDEEConstants, 'MIN_FAT_G')
        assert hasattr(TDEEConstants, 'MAX_FAT_G')
        assert hasattr(TDEEConstants, 'MIN_CARBS_G')

        assert TDEEConstants.MIN_PROTEIN_G == 60
        assert TDEEConstants.MAX_PROTEIN_G == 300
        assert TDEEConstants.MIN_FAT_G == 40
        assert TDEEConstants.MAX_FAT_G == 150
        assert TDEEConstants.MIN_CARBS_G == 50

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

            # Verify weight-based protein (should be same regardless of TDEE)
            expected_protein = 80 * 1.6  # bulk = 1.6 g/kg
            assert response.macros.protein == pytest.approx(expected_protein, abs=1)

    # ===== DIFFERENT WEIGHTS TEST =====

    def test_protein_scales_with_weight(self, service, base_request):
        """Verify protein scales proportionally with body weight."""
        base_request.goal = Goal.RECOMP
        base_request.weight = 80
        response_80kg = service.calculate_tdee(base_request)

        base_request.weight = 100
        response_100kg = service.calculate_tdee(base_request)

        # Protein should scale with weight (1.8 g/kg for recomp)
        assert response_100kg.macros.protein > response_80kg.macros.protein
        assert response_80kg.macros.protein == pytest.approx(80 * 1.8, abs=1)
        assert response_100kg.macros.protein == pytest.approx(100 * 1.8, abs=1)

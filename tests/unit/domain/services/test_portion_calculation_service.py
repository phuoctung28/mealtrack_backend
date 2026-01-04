"""Tests for PortionCalculationService."""
import pytest
from src.domain.services.portion_calculation_service import PortionCalculationService


class TestPortionCalculationService:
    """Test portion calculation logic."""

    def setup_method(self):
        self.service = PortionCalculationService()

    def test_snack_returns_fixed_range(self):
        # Daily: 2000, snack = 12% of daily = 240 (10-15% range)
        result = self.service.calculate_snack_target(2000)
        assert result.target_calories == 240  # 12% of 2000
        assert result.min_calories == 200  # 10% of 2000
        assert result.max_calories == 300  # 15% of 2000

    def test_main_meal_divides_by_meals_per_day(self):
        # Daily: 1700, main meal = 33% of daily = 561
        result = self.service.calculate_main_meal_target(1700, 2)
        assert result.target_calories == 561  # 33% of 1700

    def test_main_meal_with_3_meals(self):
        # Daily: 2100, 3 meals → (2100-300)/3 = 600
        result = self.service.calculate_main_meal_target(2100, 3)
        assert result.target_calories == 600

    def test_omad_returns_full_daily(self):
        result = self.service.calculate_omad_target(1700)
        assert result.target_calories == 1700

    def test_get_target_for_meal_type_snack(self):
        result = self.service.get_target_for_meal_type("snack", 2000, 3)
        assert result.target_calories == 225

    def test_get_target_for_meal_type_main(self):
        result = self.service.get_target_for_meal_type("main", 1700, 2)
        assert result.target_calories == 700

    def test_get_target_for_meal_type_omad(self):
        result = self.service.get_target_for_meal_type("omad", 1700, 2)
        assert result.target_calories == 1700

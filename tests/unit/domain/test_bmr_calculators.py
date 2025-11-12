"""
Unit tests for BMR calculator services.
"""
import pytest

from src.domain.services.bmr_calculator import (
    MifflinStJeorCalculator,
    KatchMcArdleCalculator,
    BMRCalculatorFactory
)
from src.domain.model import Sex


class TestMifflinStJeorCalculator:
    """Test Mifflin-St Jeor BMR calculation."""
    
    def test_calculate_bmr_for_male(self):
        """Test BMR calculation for male using Mifflin-St Jeor."""
        calculator = MifflinStJeorCalculator()
        
        # Test case: 30-year-old male, 80kg, 175cm
        bmr = calculator.calculate(
            weight_kg=80,
            height_cm=175,
            age=30,
            sex=Sex.MALE
        )
        
        # Formula: 10 * weight + 6.25 * height - 5 * age + 5
        # Expected: 10*80 + 6.25*175 - 5*30 + 5 = 800 + 1093.75 - 150 + 5 = 1748.75
        assert bmr == pytest.approx(1748.75, abs=0.1)
    
    def test_calculate_bmr_for_female(self):
        """Test BMR calculation for female using Mifflin-St Jeor."""
        calculator = MifflinStJeorCalculator()
        
        # Test case: 28-year-old female, 65kg, 165cm
        bmr = calculator.calculate(
            weight_kg=65,
            height_cm=165,
            age=28,
            sex=Sex.FEMALE
        )
        
        # Formula: 10 * weight + 6.25 * height - 5 * age - 161
        # Expected: 10*65 + 6.25*165 - 5*28 - 161 = 650 + 1031.25 - 140 - 161 = 1380.25
        assert bmr == pytest.approx(1380.25, abs=0.1)
    
    def test_formula_name(self):
        """Test that calculator returns correct formula name."""
        calculator = MifflinStJeorCalculator()
        assert calculator.get_formula_name() == "Mifflin-St Jeor"


class TestKatchMcArdleCalculator:
    """Test Katch-McArdle BMR calculation."""
    
    def test_calculate_bmr_with_body_fat(self):
        """Test BMR calculation using Katch-McArdle formula."""
        calculator = KatchMcArdleCalculator()
        
        # Test case: 80kg with 20% body fat
        # Lean mass = 80 * (1 - 0.20) = 64kg
        # BMR = 370 + (21.6 * 64) = 370 + 1382.4 = 1752.4
        bmr = calculator.calculate(
            weight_kg=80,
            height_cm=175,  # Not used in Katch-McArdle
            age=30,         # Not used in Katch-McArdle
            sex=Sex.MALE,   # Not used in Katch-McArdle
            body_fat_pct=20.0
        )
        
        assert bmr == pytest.approx(1752.4, abs=0.1)
    
    def test_calculate_bmr_different_body_fat(self):
        """Test BMR calculation with different body fat percentage."""
        calculator = KatchMcArdleCalculator()
        
        # Test case: 65kg with 30% body fat
        # Lean mass = 65 * (1 - 0.30) = 45.5kg
        # BMR = 370 + (21.6 * 45.5) = 370 + 982.8 = 1352.8
        bmr = calculator.calculate(
            weight_kg=65,
            height_cm=165,
            age=28,
            sex=Sex.FEMALE,
            body_fat_pct=30.0
        )
        
        assert bmr == pytest.approx(1352.8, abs=0.1)
    
    def test_raises_error_without_body_fat(self):
        """Test that calculator raises error when body fat is not provided."""
        calculator = KatchMcArdleCalculator()
        
        with pytest.raises(ValueError, match="requires body fat percentage"):
            calculator.calculate(
                weight_kg=80,
                height_cm=175,
                age=30,
                sex=Sex.MALE,
                body_fat_pct=None
            )
    
    def test_formula_name(self):
        """Test that calculator returns correct formula name."""
        calculator = KatchMcArdleCalculator()
        assert calculator.get_formula_name() == "Katch-McArdle"


class TestBMRCalculatorFactory:
    """Test BMR calculator factory."""
    
    def test_factory_returns_katch_mcardle_with_body_fat(self):
        """Test that factory returns Katch-McArdle when body fat is available."""
        calculator = BMRCalculatorFactory.get_calculator(has_body_fat=True)
        assert isinstance(calculator, KatchMcArdleCalculator)
        assert calculator.get_formula_name() == "Katch-McArdle"
    
    def test_factory_returns_mifflin_st_jeor_without_body_fat(self):
        """Test that factory returns Mifflin-St Jeor when body fat is not available."""
        calculator = BMRCalculatorFactory.get_calculator(has_body_fat=False)
        assert isinstance(calculator, MifflinStJeorCalculator)
        assert calculator.get_formula_name() == "Mifflin-St Jeor"


class TestBMRCalculatorComparison:
    """Compare results between different calculators."""
    
    def test_katch_mcardle_vs_mifflin_st_jeor(self):
        """Compare BMR calculations between formulas for same person."""
        # Person: 30-year-old male, 80kg, 175cm, 20% body fat
        
        # Mifflin-St Jeor
        mifflin = MifflinStJeorCalculator()
        bmr_mifflin = mifflin.calculate(
            weight_kg=80,
            height_cm=175,
            age=30,
            sex=Sex.MALE
        )
        
        # Katch-McArdle
        katch = KatchMcArdleCalculator()
        bmr_katch = katch.calculate(
            weight_kg=80,
            height_cm=175,
            age=30,
            sex=Sex.MALE,
            body_fat_pct=20.0
        )
        
        # Both should give reasonable results (within ~5% of each other for typical individuals)
        # Mifflin-St Jeor: 1748.75
        # Katch-McArdle: 1752.4
        assert bmr_mifflin == pytest.approx(1748.75, abs=0.1)
        assert bmr_katch == pytest.approx(1752.4, abs=0.1)
        
        # Difference should be small (< 100 calories for this example)
        assert abs(bmr_katch - bmr_mifflin) < 100


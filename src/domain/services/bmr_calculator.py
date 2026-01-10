"""
BMR (Basal Metabolic Rate) calculation services.

Provides different formulas for calculating BMR based on available user data:
- Mifflin-St Jeor: Standard formula using age, weight, height, and sex
- Katch-McArdle: More accurate formula using lean body mass (requires body fat %)
"""
from abc import ABC, abstractmethod
from typing import Optional

from src.domain.model.user import Sex


class BMRCalculator(ABC):
    """Abstract base class for BMR calculation strategies."""
    
    @abstractmethod
    def calculate(
        self,
        weight_kg: float,
        height_cm: float,
        age: int,
        sex: Sex,
        body_fat_pct: Optional[float] = None
    ) -> float:
        """Calculate BMR based on user attributes."""
        pass
    
    @abstractmethod
    def get_formula_name(self) -> str:
        """Return the name of the formula used."""
        pass


class MifflinStJeorCalculator(BMRCalculator):
    """
    Mifflin-St Jeor BMR Calculator.
    
    Standard formula for calculating BMR without body composition data.
    Based on age, weight, height, and biological sex.
    
    Formula:
    - Men: BMR = 10 * weight(kg) + 6.25 * height(cm) - 5 * age + 5
    - Women: BMR = 10 * weight(kg) + 6.25 * height(cm) - 5 * age - 161
    """
    
    def calculate(
        self,
        weight_kg: float,
        height_cm: float,
        age: int,
        sex: Sex,
        body_fat_pct: Optional[float] = None
    ) -> float:
        """Calculate BMR using Mifflin-St Jeor equation."""
        base = 10 * weight_kg + 6.25 * height_cm - 5 * age
        
        if sex == Sex.MALE:
            return base + 5
        else:  # Female
            return base - 161
    
    def get_formula_name(self) -> str:
        """Return formula name."""
        return "Mifflin-St Jeor"


class KatchMcArdleCalculator(BMRCalculator):
    """
    Katch-McArdle BMR Calculator.
    
    More accurate formula that accounts for body composition.
    Requires body fat percentage measurement.
    
    Formula:
    - BMR = 370 + (21.6 * lean_mass_kg)
    - Where: lean_mass_kg = weight_kg * (1 - body_fat_pct / 100)
    
    This formula is generally more accurate than Mifflin-St Jeor because it
    accounts for lean body mass, which is the primary determinant of metabolic rate.
    """
    
    def calculate(
        self,
        weight_kg: float,
        height_cm: float,
        age: int,
        sex: Sex,
        body_fat_pct: Optional[float] = None
    ) -> float:
        """Calculate BMR using Katch-McArdle equation."""
        if body_fat_pct is None:
            raise ValueError("Katch-McArdle formula requires body fat percentage")
        
        # Calculate lean body mass
        lean_mass_kg = weight_kg * (1 - body_fat_pct / 100)
        
        # Katch-McArdle formula
        return 370 + (21.6 * lean_mass_kg)
    
    def get_formula_name(self) -> str:
        """Return formula name."""
        return "Katch-McArdle"


class BMRCalculatorFactory:
    """
    Factory for selecting the appropriate BMR calculator.
    
    Strategy:
    - If body fat % is available: Use Katch-McArdle (more accurate)
    - If body fat % is not available: Use Mifflin-St Jeor (standard approach)
    """
    
    @staticmethod
    def get_calculator(has_body_fat: bool) -> BMRCalculator:
        """
        Get the appropriate BMR calculator based on available data.
        
        Args:
            has_body_fat: Whether body fat percentage is available
            
        Returns:
            BMRCalculator instance (Katch-McArdle if body fat available, else Mifflin-St Jeor)
        """
        if has_body_fat:
            return KatchMcArdleCalculator()
        else:
            return MifflinStJeorCalculator()


from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Sex(Enum):
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(Enum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    EXTRA = "extra"


class Goal(Enum):
    MAINTENANCE = "maintenance"
    CUTTING = "cutting"
    BULKING = "bulking"


class UnitSystem(Enum):
    METRIC = "metric"
    IMPERIAL = "imperial"


@dataclass
class TdeeRequest:
    """Domain model for TDEE calculation request."""
    age: int
    sex: Sex
    height: float
    weight: float
    body_fat_pct: Optional[float]
    activity_level: ActivityLevel
    goal: Goal
    unit_system: UnitSystem = UnitSystem.METRIC
    
    def __post_init__(self):
        """Validate invariants."""
        if not (13 <= self.age <= 120):
            raise ValueError(f"Age must be between 13 and 120: {self.age}")
        
        if self.unit_system == UnitSystem.METRIC:
            if not (100 <= self.height <= 272):
                raise ValueError(f"Height must be between 100-272 cm: {self.height}")
        else:
            if not (39 <= self.height <= 107):
                raise ValueError(f"Height must be between 39-107 inches: {self.height}")
        
        if self.unit_system == UnitSystem.METRIC:
            if not (30 <= self.weight <= 250):
                raise ValueError(f"Weight must be between 30-250 kg: {self.weight}")
        else:
            if not (66 <= self.weight <= 551):
                raise ValueError(f"Weight must be between 66-551 lbs: {self.weight}")
        
        if self.body_fat_pct is not None:
            if not (5 <= self.body_fat_pct <= 55):
                raise ValueError(f"Body fat percentage must be between 5-55%: {self.body_fat_pct}")
    
    @property
    def height_cm(self) -> float:
        """Convert height to centimeters."""
        if self.unit_system == UnitSystem.METRIC:
            return self.height
        else:
            return self.height * 2.54
    
    @property
    def weight_kg(self) -> float:
        """Convert weight to kilograms."""
        if self.unit_system == UnitSystem.METRIC:
            return self.weight
        else:
            return self.weight * 0.453592


@dataclass
class MacroTargets:
    """Represents macro targets matching Flutter MacroTargets class."""
    calories: float
    protein: float
    fat: float
    carbs: float


@dataclass
class TdeeResponse:
    """Domain model for TDEE calculation response matching Flutter TdeeResult."""
    bmr: float
    tdee: float
    goal: Goal
    macros: MacroTargets
    formula_used: str | None = None  # BMR formula used (e.g., "Mifflin-St Jeor", "Katch-McArdle")
    
    def to_dict(self) -> dict:
        """Convert to dictionary format for API response."""
        result = {
            "bmr": self.bmr,
            "tdee": self.tdee,
            "goal": self.goal,
            "macros": {
                "calories": self.macros.calories,
                "protein": self.macros.protein,
                "fat": self.macros.fat,
                "carbs": self.macros.carbs
            }
        }
        if self.formula_used:
            result["formula_used"] = self.formula_used
        return result 
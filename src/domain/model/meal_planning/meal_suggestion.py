"""
Domain entities for meal suggestion system.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from src.domain.utils.timezone_utils import utc_now


class MealType(str, Enum):
    """Types of meals."""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class MealSize(str, Enum):
    """T-shirt sizing for meal portions (percentage of daily TDEE)."""
    S = "S"      # 10% of daily TDEE
    M = "M"      # 20%
    L = "L"      # 40%
    XL = "XL"    # 60%
    OMAD = "OMAD"  # 100% (One Meal A Day)


# Mapping meal sizes to TDEE percentages
MEAL_SIZE_PERCENTAGES = {
    MealSize.S: 0.10,
    MealSize.M: 0.20,
    MealSize.L: 0.40,
    MealSize.XL: 0.60,
    MealSize.OMAD: 1.00,
}


class SuggestionStatus(str, Enum):
    """Status of a meal suggestion."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class Ingredient:
    """Value object representing an ingredient."""
    name: str
    amount: float
    unit: str


@dataclass
class RecipeStep:
    """Value object representing a recipe instruction step."""
    step: int
    instruction: str
    duration_minutes: Optional[int] = None


@dataclass
class MacroEstimate:
    """Value object for macro estimates with portion multiplication."""
    calories: int
    protein: float
    carbs: float
    fat: float

    def multiply(self, factor: int) -> "MacroEstimate":
        """Apply portion multiplier (1x, 2x, 3x, 4x)."""
        return MacroEstimate(
            calories=int(self.calories * factor),
            protein=round(self.protein * factor, 1),
            carbs=round(self.carbs * factor, 1),
            fat=round(self.fat * factor, 1),
        )


@dataclass
class MealSuggestion:
    """Domain entity representing a generated meal suggestion."""
    id: str
    session_id: str
    user_id: str
    meal_name: str
    description: str
    meal_type: MealType
    macros: MacroEstimate
    ingredients: List[Ingredient]
    recipe_steps: List[RecipeStep]
    prep_time_minutes: int
    confidence_score: float = 0.9
    status: SuggestionStatus = SuggestionStatus.PENDING
    generated_at: datetime = field(default_factory=utc_now)

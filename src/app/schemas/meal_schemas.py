"""
App layer DTOs for meal-related operations.
Domain-agnostic - used by handlers, mapped to API DTOs at the presentation layer.
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ParsedFoodItemDto:
    """DTO for a parsed food item (app layer)."""
    name: str
    quantity: float
    unit: str
    protein: float
    carbs: float
    fat: float
    data_source: Optional[str] = None
    fdc_id: Optional[int] = None


@dataclass
class ParseMealTextResponseDto:
    """DTO for parse meal text command response (app layer)."""
    items: List[ParsedFoodItemDto]
    total_protein: float
    total_carbs: float
    total_fat: float

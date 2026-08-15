"""
App layer DTOs for meal-related operations.
Domain-agnostic - used by handlers, mapped to API DTOs at the presentation layer.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedFoodItemDto:
    """DTO for a parsed food item (app layer)."""

    name: str
    quantity: float
    unit: str
    protein: float
    carbs: float
    fat: float
    fiber: float = 0.0
    sugar: float = 0.0
    data_source: str | None = None
    fdc_id: int | None = None
    allowed_units: list[dict[str, Any]] | None = None


@dataclass
class ParseMealTextResponseDto:
    """DTO for parse meal text command response (app layer)."""

    items: list[ParsedFoodItemDto]
    total_protein: float
    total_carbs: float
    total_fat: float
    emoji: str | None = None

"""
Serving unit model representing available units for a food item.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ServingUnit:
    """Represents a unit of measurement for a food item with gram conversion."""
    unit: str  # "cup", "tbsp", "piece", "g"
    gram_weight: float  # grams per 1 unit
    description: str = ""  # "1 cup, chopped" or "1 large egg"

    def to_dict(self) -> dict:
        return {
            "unit": self.unit,
            "gram_weight": self.gram_weight,
            "description": self.description,
        }

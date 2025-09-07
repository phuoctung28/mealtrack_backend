"""
Command to create a manual meal from a list of USDA FDC items with portions.
"""
from dataclasses import dataclass
from typing import List

from src.app.events.base import Command


@dataclass
class ManualMealItem:
    fdc_id: int
    quantity: float  # in grams or unit-specified grams base
    unit: str        # unit name, e.g., "g"


@dataclass
class CreateManualMealCommand(Command):
    user_id: str
    items: List[ManualMealItem]
    dish_name: str

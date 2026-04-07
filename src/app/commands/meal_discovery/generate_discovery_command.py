"""Command for generating a batch of discovery meals."""
from dataclasses import dataclass, field
from typing import List, Optional

from src.app.events.base import Command


@dataclass
class GenerateDiscoveryCommand(Command):
    """
    Command to generate 10-20 lightweight discovery meals.

    Used by the Meal Discovery screen (NM-67) to browse diverse meal options
    before committing to a full recipe generation.
    """

    user_id: str
    meal_type: Optional[str] = None        # auto-detected from time if not set
    cuisine_filter: Optional[str] = None   # vietnamese/asian/western/etc
    cooking_time: Optional[str] = None     # quick/medium/long
    calorie_level: Optional[str] = None    # light/regular/hearty
    macro_focus: Optional[str] = None      # high_protein/high_carb/low_fat
    exclude_ids: List[str] = field(default_factory=list)
    language: str = "en"

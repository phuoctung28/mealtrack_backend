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
    meal_type: Optional[str] = None        # breakfast/lunch/dinner/snack
    cuisine_filter: Optional[str] = None   # vietnamese/asian/western
    exclude_ids: List[str] = field(default_factory=list)
    language: str = "en"

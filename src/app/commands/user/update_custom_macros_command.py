"""Command to update custom macro targets."""
from dataclasses import dataclass
from typing import Optional

from src.app.events.base import Command


@dataclass
class UpdateCustomMacrosCommand(Command):
    """Set or clear custom macro overrides. All-null = reset, all-set = custom."""
    user_id: str
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None

"""
Update user profile command.
"""
from dataclasses import dataclass
from typing import Dict, Any

from src.app.events.base import Command


@dataclass
class UpdateUserProfileCommand(Command):
    """Command to update user profile."""
    user_profile_id: str
    updates: Dict[str, Any]
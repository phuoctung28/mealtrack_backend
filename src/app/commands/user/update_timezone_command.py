"""Command to update user timezone."""
from dataclasses import dataclass
from uuid import UUID

from src.app.events.base import Command


@dataclass
class UpdateTimezoneCommand(Command):
    """Command to update user's timezone."""
    user_id: UUID
    timezone: str  # IANA timezone identifier

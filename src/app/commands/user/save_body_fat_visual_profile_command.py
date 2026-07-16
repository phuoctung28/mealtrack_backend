"""Command to append a visual body-fat profile selection."""

from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class SaveBodyFatVisualProfileCommand(Command):
    """Append a visual body-fat profile record for a user."""

    user_id: str
    schema_version: int
    range_catalog_version: int
    sex_at_selection: str
    current_range_id: str
    target_range_id: str | None

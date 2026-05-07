"""Command to delete a weight entry."""

from dataclasses import dataclass


@dataclass
class DeleteWeightEntryCommand:
    """Delete a weight entry."""

    user_id: str
    entry_id: str

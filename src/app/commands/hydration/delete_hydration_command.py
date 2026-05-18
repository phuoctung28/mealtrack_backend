"""Command to delete a hydration log entry."""

from dataclasses import dataclass


@dataclass
class DeleteHydrationCommand:
    hydration_entry_id: str
    user_id: str  # Required for ownership verification

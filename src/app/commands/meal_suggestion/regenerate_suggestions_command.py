"""Regenerate suggestions command."""
from dataclasses import dataclass
from typing import List


@dataclass
class RegenerateSuggestionsCommand:
    """Command to regenerate 3 NEW suggestions (excludes shown)."""

    user_id: str
    session_id: str
    exclude_ids: List[str]

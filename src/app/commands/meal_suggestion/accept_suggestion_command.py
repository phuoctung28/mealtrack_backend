"""Accept suggestion command."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AcceptSuggestionCommand:
    """Command to accept suggestion with portion multiplier."""

    user_id: str
    suggestion_id: str
    portion_multiplier: int
    consumed_at: Optional[datetime]

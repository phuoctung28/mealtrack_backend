"""Movement entry domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


def _movement_id() -> str:
    return f"mvmt_{uuid.uuid4().hex}"


@dataclass
class MovementEntry:
    user_id: str
    activity_name: str
    duration_min: int
    kcal_burned: float
    intensity: str
    logged_at: datetime
    id: str = field(default_factory=_movement_id)
    activity_id: Optional[str] = None
    source: str = "manual"
    include_in_balance: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_included_in_balance(self) -> bool:
        return self.include_in_balance

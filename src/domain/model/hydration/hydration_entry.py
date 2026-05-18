"""HydrationEntry aggregate with DrinkType enum.

Domain model representing a single hydration log entry.
Only zero-calorie drinks are tracked; caloric beverages belong in meal logging.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from src.domain.utils.timezone_utils import utc_now

# Per-entry volume bounds (application-enforced at API layer in Phase 2).
# Goal bounds (500–4000 ml) are enforced on users.hydration_goal_ml.
_VOLUME_MIN_ML = 1
_VOLUME_MAX_ML = 2000


class DrinkType(Enum):
    """Zero-calorie drink categories eligible for hydration tracking."""

    WATER = "WATER"
    SPARKLING_WATER = "SPARKLING_WATER"
    PLAIN_TEA = "PLAIN_TEA"
    BLACK_COFFEE = "BLACK_COFFEE"
    HERBAL_TEA = "HERBAL_TEA"

    def __str__(self) -> str:
        return self.value


@dataclass
class HydrationEntry:
    """Aggregate root for a single hydration log entry.

    volume_ml is bounded to [1, 2000] per entry.
    The user's daily hydration goal (users.hydration_goal_ml) is bounded
    to [500, 4000] — enforced at the API layer.
    """

    hydration_entry_id: str
    user_id: str
    drink_type: DrinkType
    volume_ml: int               # validated 1–2000 per entry
    logged_at: datetime          # tz-aware UTC
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Enforce domain invariants."""
        try:
            uuid.UUID(self.hydration_entry_id)
        except ValueError as exc:
            raise ValueError(
                f"Invalid UUID format for hydration_entry_id: {self.hydration_entry_id}"
            ) from exc

        try:
            uuid.UUID(self.user_id)
        except ValueError as exc:
            raise ValueError(
                f"Invalid UUID format for user_id: {self.user_id}"
            ) from exc

        if not (_VOLUME_MIN_ML <= self.volume_ml <= _VOLUME_MAX_ML):
            raise ValueError(
                f"volume_ml must be between {_VOLUME_MIN_ML} and {_VOLUME_MAX_ML}, "
                f"got {self.volume_ml}"
            )

    @classmethod
    def create_new(
        cls,
        user_id: str,
        drink_type: DrinkType,
        volume_ml: int,
        logged_at: datetime,
    ) -> "HydrationEntry":
        """Factory method — generates a new UUID and sets created_at to now."""
        return cls(
            hydration_entry_id=str(uuid.uuid4()),
            user_id=user_id,
            drink_type=drink_type,
            volume_ml=volume_ml,
            logged_at=logged_at,
            created_at=utc_now(),
        )

"""HydrationEntry domain aggregate — persisted hydration log row."""

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from src.domain.model.hydration.hydration_enums import HydrationSource
from src.domain.utils.timezone_utils import utc_now


@dataclass
class HydrationEntry:
    """
    Aggregate root representing a single hydration log entry for a user.
    """

    entry_id: str
    user_id: str
    drink_id: str
    volume_ml: int
    credited_ml: int
    source: HydrationSource  # "hydration" or "caloric_drink"
    meal_id: str | None
    logged_at: datetime
    created_at: datetime
    is_deleted: bool = False

    def __post_init__(self) -> None:
        """Validate domain invariants."""
        if self.volume_ml <= 0:
            raise ValueError(f"volume_ml must be positive, got {self.volume_ml}")
        if self.credited_ml < 0:
            raise ValueError(
                f"credited_ml must be non-negative, got {self.credited_ml}"
            )
        if self.source not in (
            HydrationSource.HYDRATION,
            HydrationSource.CALORIC_DRINK,
            "hydration",
            "caloric_drink",
        ):
            raise ValueError(
                f"source must be 'hydration' or 'caloric_drink', got '{self.source}'"
            )
        if self.source in (HydrationSource.CALORIC_DRINK, "caloric_drink") and self.meal_id is None:
            raise ValueError("meal_id is required when source is 'caloric_drink'")

    @classmethod
    def create(
        cls,
        user_id: str,
        drink_id: str,
        volume_ml: int,
        credited_ml: int,
        source: HydrationSource | str,
        meal_id: str | None = None,
    ) -> "HydrationEntry":
        """Factory method to create a new hydration log entry."""
        now = utc_now()
        return cls(
            entry_id=str(uuid4()),
            user_id=user_id,
            drink_id=drink_id,
            volume_ml=volume_ml,
            credited_ml=credited_ml,
            source=source,
            meal_id=meal_id,
            logged_at=now,
            created_at=now,
        )

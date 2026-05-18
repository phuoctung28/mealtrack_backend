"""WorkoutLog aggregate root with WorkoutType and Intensity enums.

Domain model representing a single logged workout session.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from src.domain.utils.timezone_utils import utc_now


class WorkoutType(Enum):
    """Supported workout categories for MET-based calorie estimation."""

    RUNNING = "RUNNING"
    CYCLING = "CYCLING"
    SWIMMING = "SWIMMING"
    WALKING = "WALKING"
    HIIT = "HIIT"
    STRENGTH = "STRENGTH"
    YOGA = "YOGA"
    PILATES = "PILATES"
    HIKING = "HIKING"
    ROWING = "ROWING"
    BOXING = "BOXING"
    DANCE = "DANCE"
    OTHER = "OTHER"

    def __str__(self) -> str:
        return self.value


class Intensity(Enum):
    """Workout intensity levels mapped to MET multipliers."""

    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    VIGOROUS = "VIGOROUS"

    def __str__(self) -> str:
        return self.value


@dataclass
class WorkoutLog:
    """Aggregate root for a single workout session.

    Calorie burn is estimated via the MET formula:
        kcal = met_value × weight_kg_snapshot × (duration_minutes / 60)

    Both weight_kg_snapshot and estimated_burn_kcal may be None when the
    user's profile has no recorded weight.
    """

    workout_log_id: str
    user_id: str
    workout_type: WorkoutType
    intensity: Intensity
    duration_minutes: int          # validated > 0
    logged_at: datetime            # tz-aware UTC
    met_value: float               # snapshot from MET_TABLE at log time
    weight_kg_snapshot: Optional[float]   # None when user has no weight on record
    estimated_burn_kcal: Optional[float]  # None when weight_kg_snapshot is None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Enforce domain invariants."""
        try:
            uuid.UUID(self.workout_log_id)
        except ValueError as exc:
            raise ValueError(
                f"Invalid UUID format for workout_log_id: {self.workout_log_id}"
            ) from exc

        try:
            uuid.UUID(self.user_id)
        except ValueError as exc:
            raise ValueError(
                f"Invalid UUID format for user_id: {self.user_id}"
            ) from exc

        if self.duration_minutes <= 0:
            raise ValueError(
                f"duration_minutes must be > 0, got {self.duration_minutes}"
            )

    @classmethod
    def create_new(
        cls,
        user_id: str,
        workout_type: WorkoutType,
        intensity: Intensity,
        duration_minutes: int,
        logged_at: datetime,
        met_value: float,
        weight_kg_snapshot: Optional[float],
        estimated_burn_kcal: Optional[float],
        notes: Optional[str] = None,
    ) -> "WorkoutLog":
        """Factory method — generates a new UUID and sets created_at to now."""
        return cls(
            workout_log_id=str(uuid.uuid4()),
            user_id=user_id,
            workout_type=workout_type,
            intensity=intensity,
            duration_minutes=duration_minutes,
            logged_at=logged_at,
            met_value=met_value,
            weight_kg_snapshot=weight_kg_snapshot,
            estimated_burn_kcal=estimated_burn_kcal,
            notes=notes,
            created_at=utc_now(),
        )

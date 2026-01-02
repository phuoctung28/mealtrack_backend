"""Portion target value object."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PortionTarget:
    """Immutable portion target for meal generation."""
    target_calories: int
    min_calories: int
    max_calories: int
    meals_per_day: int

    def __post_init__(self) -> None:
        """Validate constraints."""
        if self.target_calories < 0:
            raise ValueError("target_calories must be positive")
        if self.min_calories > self.target_calories:
            raise ValueError("min_calories cannot exceed target_calories")
        if self.max_calories < self.target_calories:
            raise ValueError("max_calories cannot be less than target_calories")

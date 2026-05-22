"""HydrationSummary — value object for daily hydration totals."""

from dataclasses import dataclass


@dataclass
class HydrationSummary:
    """
    Value object representing daily hydration progress.

    percentage is derived from consumed_ml and goal_ml and is set
    automatically in __post_init__.
    """

    consumed_ml: int
    goal_ml: int
    percentage: float = 0.0

    def __post_init__(self) -> None:
        """Compute and cap percentage."""
        if self.goal_ml > 0:
            self.percentage = min(
                100.0, round(self.consumed_ml / self.goal_ml * 100, 1)
            )
        else:
            self.percentage = 0.0

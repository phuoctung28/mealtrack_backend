"""Command to update a user's daily hydration goal."""

from dataclasses import dataclass


@dataclass
class UpdateHydrationGoalCommand:
    user_id: str
    goal_ml: int  # Validated bounds: 500–4000 ml (enforced at API and handler layers)

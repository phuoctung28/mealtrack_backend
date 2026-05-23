"""Hydration goal calculation."""

from src.domain.model.user.core_user import UserProfileDomainModel


def resolve_hydration_goal_ml(profile: UserProfileDomainModel) -> int:
    """Return daily hydration goal in ml.

    Uses custom override if set; otherwise 35 ml per kg body weight.
    """
    if profile.daily_water_goal_ml is not None:
        return profile.daily_water_goal_ml
    return round(35 * profile.weight_kg)

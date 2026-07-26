"""Canonical validation for planned-training fields."""


def normalize_training_pair(
    days: int, minutes: int, *, allow_legacy: bool = False
) -> tuple[int, int]:
    """Validate a training pair and normalize the temporary legacy no-training value."""
    if not 0 <= days <= 7:
        raise ValueError("Training days per week must be between 0 and 7")
    if days == 0:
        if minutes == 0 or (allow_legacy and minutes == 15):
            return 0, 0
        raise ValueError("Training minutes must be 0 when training days are 0")
    if not 15 <= minutes <= 180:
        raise ValueError("Training minutes per session must be between 15 and 180")
    return days, minutes

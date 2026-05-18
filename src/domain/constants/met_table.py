"""MET (Metabolic Equivalent of Task) reference table for calorie burn estimation.

Source: Ainsworth BE et al. (2011). 2011 Compendium of Physical Activities:
        a second update of codes and MET values. Medicine & Science in Sports &
        Exercise, 43(8), 1575–1581.

Usage:
    met = MET_TABLE.get((WorkoutType.RUNNING, Intensity.MODERATE))
    kcal = estimate_burn(met, weight_kg=75.0, minutes=45)

Notes:
    - HIIT has no LIGHT intensity (by definition high-effort).
    - BOXING has no LIGHT intensity (even "light" boxing is moderate effort).
    - PILATES has no VIGOROUS intensity (ceiling capped at MODERATE per compendium).
    - estimate_burn returns None when weight_kg is None (user has no recorded weight).
"""

from typing import Optional

from src.domain.model.workout.workout_log import Intensity, WorkoutType

# 35 entries covering all 13 workout types.
# Keys: (WorkoutType, Intensity) — use MET_TABLE.get() to handle missing combos.
MET_TABLE: dict[tuple[WorkoutType, Intensity], float] = {
    # Running
    (WorkoutType.RUNNING, Intensity.LIGHT): 6.0,
    (WorkoutType.RUNNING, Intensity.MODERATE): 8.3,
    (WorkoutType.RUNNING, Intensity.VIGOROUS): 11.5,
    # Cycling
    (WorkoutType.CYCLING, Intensity.LIGHT): 4.0,
    (WorkoutType.CYCLING, Intensity.MODERATE): 6.8,
    (WorkoutType.CYCLING, Intensity.VIGOROUS): 10.0,
    # Swimming
    (WorkoutType.SWIMMING, Intensity.LIGHT): 5.8,
    (WorkoutType.SWIMMING, Intensity.MODERATE): 8.3,
    (WorkoutType.SWIMMING, Intensity.VIGOROUS): 10.0,
    # Walking
    (WorkoutType.WALKING, Intensity.LIGHT): 2.8,
    (WorkoutType.WALKING, Intensity.MODERATE): 3.5,
    (WorkoutType.WALKING, Intensity.VIGOROUS): 4.5,
    # HIIT — no LIGHT entry (inherently high-effort activity)
    (WorkoutType.HIIT, Intensity.MODERATE): 8.0,
    (WorkoutType.HIIT, Intensity.VIGOROUS): 12.0,
    # Strength training
    (WorkoutType.STRENGTH, Intensity.LIGHT): 3.5,
    (WorkoutType.STRENGTH, Intensity.MODERATE): 5.0,
    (WorkoutType.STRENGTH, Intensity.VIGOROUS): 6.0,
    # Yoga
    (WorkoutType.YOGA, Intensity.LIGHT): 2.5,
    (WorkoutType.YOGA, Intensity.MODERATE): 3.0,
    (WorkoutType.YOGA, Intensity.VIGOROUS): 4.0,
    # Pilates — no VIGOROUS entry (compendium ceiling at moderate effort)
    (WorkoutType.PILATES, Intensity.LIGHT): 2.8,
    (WorkoutType.PILATES, Intensity.MODERATE): 3.8,
    # Hiking
    (WorkoutType.HIKING, Intensity.LIGHT): 5.3,
    (WorkoutType.HIKING, Intensity.MODERATE): 6.0,
    (WorkoutType.HIKING, Intensity.VIGOROUS): 7.3,
    # Rowing
    (WorkoutType.ROWING, Intensity.LIGHT): 4.8,
    (WorkoutType.ROWING, Intensity.MODERATE): 7.0,
    (WorkoutType.ROWING, Intensity.VIGOROUS): 8.5,
    # Boxing — no LIGHT entry (even light boxing is moderate effort)
    (WorkoutType.BOXING, Intensity.MODERATE): 7.8,
    (WorkoutType.BOXING, Intensity.VIGOROUS): 9.8,
    # Dance
    (WorkoutType.DANCE, Intensity.LIGHT): 3.5,
    (WorkoutType.DANCE, Intensity.MODERATE): 4.8,
    (WorkoutType.DANCE, Intensity.VIGOROUS): 6.5,
    # Other (generic fallback values)
    (WorkoutType.OTHER, Intensity.LIGHT): 3.0,
    (WorkoutType.OTHER, Intensity.MODERATE): 5.0,
    (WorkoutType.OTHER, Intensity.VIGOROUS): 7.0,
}


def estimate_burn(
    met: float, weight_kg: Optional[float], minutes: int
) -> Optional[float]:
    """Estimate calorie burn using the MET formula.

    Formula: kcal = MET × weight_kg × (minutes / 60)

    Args:
        met: MET value from MET_TABLE for the workout type and intensity.
        weight_kg: User's body weight in kilograms. Pass None when unknown.
        minutes: Workout duration in minutes (must be > 0).

    Returns:
        Estimated kilocalories burned rounded to 1 decimal place,
        or None when weight_kg is None (weight not recorded for user).
    """
    if weight_kg is None:
        return None
    return round(met * weight_kg * (minutes / 60.0), 1)

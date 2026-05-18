"""Unit tests for workout/hydration domain models and MET table.

Covers:
  - estimate_burn: weight-missing path, sanity value, zero-weight guard
  - WorkoutLog: create_new factory, UUID validation, duration invariant
  - HydrationEntry: create_new factory, volume bounds, UUID validation
  - MET_TABLE: entry count, missing combos (HIIT/BOXING no LIGHT, PILATES no VIGOROUS)
"""

import uuid
from datetime import datetime, timezone

import pytest

from src.domain.constants.met_table import MET_TABLE, estimate_burn
from src.domain.model.hydration.hydration_entry import DrinkType, HydrationEntry
from src.domain.model.workout.workout_log import Intensity, WorkoutLog, WorkoutType


# ---------------------------------------------------------------------------
# estimate_burn
# ---------------------------------------------------------------------------

class TestEstimateBurn:
    def test_returns_none_when_weight_is_none(self):
        assert estimate_burn(8.3, None, 45) is None

    def test_sanity_value(self):
        # 8.3 × 75 × (45/60) = 8.3 × 75 × 0.75 = 467.25 → round(1) = wait...
        # Actually: 8.3 * 75 * 0.75 = 466.875 → rounds to 466.9
        result = estimate_burn(8.3, 75, 45)
        assert result == 466.9

    def test_rounds_to_one_decimal(self):
        # 6.0 × 70 × (30/60) = 210.0 exactly
        assert estimate_burn(6.0, 70, 30) == 210.0

    def test_zero_weight_returns_zero(self):
        # weight=0 is technically valid input (not None); result is 0.0
        assert estimate_burn(8.3, 0.0, 45) == 0.0

    def test_fractional_result(self):
        # 5.0 × 60 × (45/60) = 225.0
        assert estimate_burn(5.0, 60, 45) == 225.0


# ---------------------------------------------------------------------------
# MET_TABLE coverage
# ---------------------------------------------------------------------------

class TestMetTable:
    def test_entry_count_at_least_35(self):
        assert len(MET_TABLE) >= 35

    def test_all_13_workout_types_present(self):
        types_present = {wt for wt, _ in MET_TABLE}
        assert types_present == set(WorkoutType)

    def test_hiit_has_no_light_entry(self):
        assert (WorkoutType.HIIT, Intensity.LIGHT) not in MET_TABLE

    def test_boxing_has_no_light_entry(self):
        assert (WorkoutType.BOXING, Intensity.LIGHT) not in MET_TABLE

    def test_pilates_has_no_vigorous_entry(self):
        assert (WorkoutType.PILATES, Intensity.VIGOROUS) not in MET_TABLE

    def test_running_all_intensities_present(self):
        for intensity in Intensity:
            assert (WorkoutType.RUNNING, intensity) in MET_TABLE

    def test_met_values_are_positive(self):
        for key, val in MET_TABLE.items():
            assert val > 0, f"Non-positive MET for {key}: {val}"


# ---------------------------------------------------------------------------
# WorkoutLog
# ---------------------------------------------------------------------------

_USER_ID = str(uuid.uuid4())
_NOW = datetime.now(timezone.utc)


class TestWorkoutLog:
    def _make(self, **overrides):
        defaults = dict(
            user_id=_USER_ID,
            workout_type=WorkoutType.RUNNING,
            intensity=Intensity.MODERATE,
            duration_minutes=30,
            logged_at=_NOW,
            met_value=8.3,
            weight_kg_snapshot=70.0,
            estimated_burn_kcal=290.5,
        )
        defaults.update(overrides)
        return WorkoutLog.create_new(**defaults)

    def test_create_new_generates_valid_uuid(self):
        log = self._make()
        uuid.UUID(log.workout_log_id)  # raises ValueError if invalid

    def test_create_new_sets_created_at(self):
        log = self._make()
        assert log.created_at is not None

    def test_duration_zero_raises(self):
        with pytest.raises(ValueError, match="duration_minutes"):
            self._make(duration_minutes=0)

    def test_duration_negative_raises(self):
        with pytest.raises(ValueError, match="duration_minutes"):
            self._make(duration_minutes=-5)

    def test_invalid_user_id_raises(self):
        with pytest.raises(ValueError, match="user_id"):
            self._make(user_id="not-a-uuid")

    def test_weight_none_accepted(self):
        log = self._make(weight_kg_snapshot=None, estimated_burn_kcal=None)
        assert log.weight_kg_snapshot is None
        assert log.estimated_burn_kcal is None

    def test_notes_optional(self):
        log = self._make(notes=None)
        assert log.notes is None

    def test_direct_construction_invalid_workout_log_id_raises(self):
        with pytest.raises(ValueError, match="workout_log_id"):
            WorkoutLog(
                workout_log_id="bad-id",
                user_id=_USER_ID,
                workout_type=WorkoutType.RUNNING,
                intensity=Intensity.MODERATE,
                duration_minutes=30,
                logged_at=_NOW,
                met_value=8.3,
                weight_kg_snapshot=70.0,
                estimated_burn_kcal=290.5,
            )


# ---------------------------------------------------------------------------
# HydrationEntry
# ---------------------------------------------------------------------------

class TestHydrationEntry:
    def _make(self, **overrides):
        defaults = dict(
            user_id=_USER_ID,
            drink_type=DrinkType.WATER,
            volume_ml=250,
            logged_at=_NOW,
        )
        defaults.update(overrides)
        return HydrationEntry.create_new(**defaults)

    def test_create_new_generates_valid_uuid(self):
        entry = self._make()
        uuid.UUID(entry.hydration_entry_id)

    def test_create_new_sets_created_at(self):
        entry = self._make()
        assert entry.created_at is not None

    def test_volume_zero_raises(self):
        with pytest.raises(ValueError, match="volume_ml"):
            self._make(volume_ml=0)

    def test_volume_exceeds_max_raises(self):
        with pytest.raises(ValueError, match="volume_ml"):
            self._make(volume_ml=2001)

    def test_volume_at_max_accepted(self):
        entry = self._make(volume_ml=2000)
        assert entry.volume_ml == 2000

    def test_volume_at_min_accepted(self):
        entry = self._make(volume_ml=1)
        assert entry.volume_ml == 1

    def test_invalid_user_id_raises(self):
        with pytest.raises(ValueError, match="user_id"):
            self._make(user_id="not-a-uuid")

    def test_all_drink_types_accepted(self):
        for drink in DrinkType:
            entry = self._make(drink_type=drink)
            assert entry.drink_type == drink

    def test_direct_construction_invalid_entry_id_raises(self):
        with pytest.raises(ValueError, match="hydration_entry_id"):
            HydrationEntry(
                hydration_entry_id="bad-id",
                user_id=_USER_ID,
                drink_type=DrinkType.WATER,
                volume_ml=250,
                logged_at=_NOW,
            )

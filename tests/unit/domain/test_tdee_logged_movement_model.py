import pytest

from src.domain.model.user import Goal, JobType, Sex, TdeeRequest, UnitSystem
from src.domain.services.tdee_service import TdeeCalculationService


def _request(
    training_days: int,
    training_minutes: int,
    job_type: JobType = JobType.DESK,
) -> TdeeRequest:
    return TdeeRequest(
        age=30,
        sex=Sex.MALE,
        height=180,
        weight=80,
        body_fat_pct=None,
        job_type=job_type,
        training_days_per_week=training_days,
        training_minutes_per_session=training_minutes,
        goal=Goal.RECOMP,
        unit_system=UnitSystem.METRIC,
    )


def test_training_volume_does_not_increase_baseline_tdee():
    service = TdeeCalculationService()

    no_training = service.calculate_tdee(_request(0, 0))
    high_training = service.calculate_tdee(_request(6, 90))

    assert no_training.bmr == pytest.approx(1780.0, abs=0.1)
    assert high_training.bmr == no_training.bmr
    assert no_training.tdee == pytest.approx(2136.0, abs=0.1)
    assert high_training.tdee == no_training.tdee


def test_job_type_still_changes_baseline_tdee():
    service = TdeeCalculationService()

    desk = service.calculate_tdee(_request(4, 60, JobType.DESK))
    on_feet = service.calculate_tdee(_request(4, 60, JobType.ON_FEET))
    physical = service.calculate_tdee(_request(4, 60, JobType.PHYSICAL))

    assert desk.bmr == pytest.approx(1780.0, abs=0.1)
    assert desk.tdee == pytest.approx(2136.0, abs=0.1)
    assert on_feet.tdee == pytest.approx(2492.0, abs=0.1)
    assert physical.tdee == pytest.approx(2848.0, abs=0.1)

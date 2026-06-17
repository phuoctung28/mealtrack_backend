import pytest

from src.domain.model.user import Goal, JobType, Sex, TdeeRequest, UnitSystem
from src.domain.services.tdee_service import TdeeCalculationService


def _request(training_days: int, training_minutes: int) -> TdeeRequest:
    return TdeeRequest(
        age=30,
        sex=Sex.MALE,
        height=180,
        weight=80,
        body_fat_pct=None,
        job_type=JobType.DESK,
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

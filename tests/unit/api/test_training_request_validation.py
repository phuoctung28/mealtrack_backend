import pytest
from pydantic import ValidationError

from src.api.schemas.request.onboarding_requests import OnboardingCompleteRequest
from src.api.schemas.request.tdee_requests import TdeeCalculationRequest


def _tdee_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "age": 30,
        "sex": "male",
        "height": 175,
        "weight": 70,
        "job_type": "desk",
        "training_days_per_week": 4,
        "training_minutes_per_session": 60,
        "goal": "recomp",
    }
    payload.update(overrides)
    return payload


def _onboarding_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "birth_year": 1995,
        "birth_month": 1,
        "birth_day": 1,
        "gender": "male",
        "height": 175,
        "weight": 70,
        "job_type": "desk",
        "training_days_per_week": 4,
        "training_minutes_per_session": 60,
        "goal": "recomp",
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    ("request_type", "payload_factory"),
    [
        (TdeeCalculationRequest, _tdee_payload),
        (OnboardingCompleteRequest, _onboarding_payload),
    ],
)
def test_no_training_requests_normalize_to_zero(request_type, payload_factory):
    request = request_type(
        **payload_factory(
            training_days_per_week=0,
            training_minutes_per_session=15,
        )
    )

    assert request.training_minutes_per_session == 0


@pytest.mark.parametrize(
    ("request_type", "payload_factory"),
    [
        (TdeeCalculationRequest, _tdee_payload),
        (OnboardingCompleteRequest, _onboarding_payload),
    ],
)
def test_training_requests_reject_zero_duration_when_training(
    request_type, payload_factory
):
    with pytest.raises(ValidationError):
        request_type(
            **payload_factory(
                training_days_per_week=1,
                training_minutes_per_session=0,
            )
        )

import pytest
from pydantic import ValidationError

from src.api.schemas.request.onboarding_requests import OnboardingCompleteRequest


def _request_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "birth_year": 1995,
        "birth_month": 1,
        "birth_day": 1,
        "gender": "female",
        "height": 165.0,
        "weight": 60.0,
        "job_type": "desk",
        "training_days_per_week": 3,
        "training_minutes_per_session": 45,
        "goal": "recomp",
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize("value", [5.0, 18.5, 55.0])
def test_onboarding_accepts_backend_compatible_target_body_fat(
    value: float,
) -> None:
    request = OnboardingCompleteRequest(
        **_request_data(target_body_fat_percentage=value)
    )

    assert request.target_body_fat_percentage == value


@pytest.mark.parametrize("value", [4.9, 55.1])
def test_onboarding_rejects_target_body_fat_outside_supported_range(
    value: float,
) -> None:
    with pytest.raises(ValidationError):
        OnboardingCompleteRequest(
            **_request_data(target_body_fat_percentage=value)
        )

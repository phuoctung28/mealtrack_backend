from src.domain.model.user.core_user import UserProfileDomainModel
import uuid


def _make_profile(**kwargs) -> UserProfileDomainModel:
    defaults = dict(
        id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        age=25, gender="male", height_cm=175.0, weight_kg=70.0,
        job_type="desk", training_days_per_week=3,
        training_minutes_per_session=45, fitness_goal="maintenance",
        meals_per_day=3,
    )
    defaults.update(kwargs)
    return UserProfileDomainModel(**defaults)


def test_profile_daily_water_goal_defaults_to_none():
    profile = _make_profile()
    assert profile.daily_water_goal_ml is None

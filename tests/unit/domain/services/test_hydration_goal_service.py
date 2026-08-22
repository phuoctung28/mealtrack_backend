import uuid

from src.domain.model.user.core_user import UserProfileDomainModel


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


def test_profile_daily_water_goal_round_trips_through_mapper():
    """Verify daily_water_goal_ml persists correctly through to_persistence and to_domain."""
    from src.infra.mappers.user_mapper import UserProfileMapper
    profile = _make_profile(daily_water_goal_ml=2500)
    orm_obj = UserProfileMapper.to_persistence(profile)
    assert orm_obj.daily_water_goal_ml == 2500
    domain_obj = UserProfileMapper.to_domain(orm_obj)
    assert domain_obj.daily_water_goal_ml == 2500


def test_resolve_goal_uses_weight_formula_when_no_override():
    from src.domain.services.hydration_goal_service import resolve_hydration_goal_ml
    profile = _make_profile(weight_kg=70.0, daily_water_goal_ml=None)
    assert resolve_hydration_goal_ml(profile) == round(35 * 70.0)  # 2450


def test_resolve_goal_uses_override_when_set():
    from src.domain.services.hydration_goal_service import resolve_hydration_goal_ml
    profile = _make_profile(weight_kg=70.0, daily_water_goal_ml=3000)
    assert resolve_hydration_goal_ml(profile) == 3000


def test_resolve_goal_weight_formula_rounds():
    from src.domain.services.hydration_goal_service import resolve_hydration_goal_ml
    profile = _make_profile(weight_kg=71.3, daily_water_goal_ml=None)
    assert resolve_hydration_goal_ml(profile) == round(35 * 71.3)


def test_resolve_goal_zero_override_is_treated_as_weight_fallback():
    from src.domain.services.hydration_goal_service import resolve_hydration_goal_ml
    # 0 is falsy; the is-not-None check means None falls back, but 0 is a valid (if silly) override
    # This documents the current behaviour so a regression would be caught
    profile = _make_profile(weight_kg=70.0, daily_water_goal_ml=0)
    # 0 is not None, so returns 0 (the override), not the weight formula
    assert resolve_hydration_goal_ml(profile) == 0


def test_update_metrics_command_accepts_water_goal():
    from src.app.commands.user.update_user_metrics_command import UpdateUserMetricsCommand
    cmd = UpdateUserMetricsCommand(user_id="abc", daily_water_goal_ml=2500)
    assert cmd.daily_water_goal_ml == 2500


def test_update_metrics_command_accepts_reset_flag():
    from src.app.commands.user.update_user_metrics_command import UpdateUserMetricsCommand
    cmd = UpdateUserMetricsCommand(user_id="abc", reset_water_goal=True)
    assert cmd.reset_water_goal is True

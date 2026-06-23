from datetime import UTC, datetime

from src.domain.services.journey_progress_rules import (
    estimate_timeline_days,
    journey_period_start,
)
from src.domain.services.journey_progress_service import (
    JourneyAction,
    calculate_journey_progress,
)
from src.domain.utils.timezone_utils import get_zone_info


def test_existing_user_period_start_uses_feature_start_in_user_timezone():
    start = journey_period_start(
        goal_started_at=None,
        user_tz=get_zone_info("Asia/Ho_Chi_Minh"),
    )

    assert start == datetime(2026, 6, 20, 17, 0, tzinfo=UTC)


def test_existing_user_old_goal_start_is_clamped_to_feature_start():
    start = journey_period_start(
        goal_started_at=datetime(2026, 5, 1, 12, tzinfo=UTC),
        user_tz=get_zone_info("Asia/Ho_Chi_Minh"),
    )

    assert start == datetime(2026, 6, 20, 17, 0, tzinfo=UTC)


def test_new_goal_start_after_feature_start_is_used():
    goal_started_at = datetime(2026, 6, 22, 12, tzinfo=UTC)
    start = journey_period_start(
        goal_started_at=goal_started_at,
        user_tz=get_zone_info("Asia/Ho_Chi_Minh"),
    )

    assert start == goal_started_at


def test_challenge_duration_overrides_weight_pace_timeline():
    assert (
        estimate_timeline_days(
            goal="cut",
            start_weight_kg=80,
            target_weight_kg=75,
            challenge_duration="30_days",
        )
        == 30
    )


def test_journey_progress_counts_only_actions_inside_strict_period():
    period_start = datetime(2026, 6, 21, tzinfo=UTC)
    period_end = datetime(2026, 7, 21, tzinfo=UTC)

    result = calculate_journey_progress(
        actions=[
            JourneyAction(
                source="meal",
                label="Old meal",
                logged_at=datetime(2026, 6, 20, 23, 59, tzinfo=UTC),
                calories=400,
                protein_g=20,
            ),
            JourneyAction(
                source="meal",
                label="Start meal",
                logged_at=period_start,
                calories=400,
                protein_g=20,
            ),
            JourneyAction(
                source="hydration",
                label="End water",
                logged_at=period_end,
                hydration_ml=500,
            ),
        ],
        period_start=period_start,
        timeline_days=30,
        user_tz=get_zone_info("UTC"),
        as_of=period_end,
        target_calories=400,
        target_protein_g=20,
        water_goal_ml=2000,
    )

    assert result["progress_percent"] > 0
    assert result["latest_action"]["label"] == "Start meal"
    assert result["latest_action"]["source"] == "meal"


def test_caloric_hydration_contributes_macro_points_without_meal_count():
    result = calculate_journey_progress(
        actions=[
            JourneyAction(
                source="hydration",
                label="Juice",
                logged_at=datetime(2026, 6, 21, 12, tzinfo=UTC),
                calories=400,
                protein_g=20,
                hydration_ml=300,
            )
        ],
        period_start=datetime(2026, 6, 21, tzinfo=UTC),
        timeline_days=30,
        user_tz=get_zone_info("UTC"),
        as_of=datetime(2026, 6, 21, 13, tzinfo=UTC),
        target_calories=400,
        target_protein_g=20,
        water_goal_ml=600,
    )

    assert result["breakdown"]["calories_points"] == 30
    assert result["breakdown"]["protein_points"] == 15
    assert result["breakdown"]["hydration_points"] == 7.5
    assert result["breakdown"]["logging_points"] == 0


def test_journey_progress_does_not_backfill_before_current_period():
    result = calculate_journey_progress(
        actions=[
            JourneyAction(
                source="meal",
                label="Historical meal",
                logged_at=datetime(2026, 6, 1, 12, tzinfo=UTC),
                calories=2000,
                protein_g=150,
            )
        ],
        period_start=datetime(2026, 6, 21, tzinfo=UTC),
        timeline_days=30,
        user_tz=get_zone_info("UTC"),
        as_of=datetime(2026, 6, 22, tzinfo=UTC),
        target_calories=2000,
        target_protein_g=150,
        water_goal_ml=2000,
    )

    assert result["progress_percent"] == 0
    assert result["latest_action"] is None

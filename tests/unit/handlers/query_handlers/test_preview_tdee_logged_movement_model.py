import pytest

from src.app.handlers.query_handlers.preview_tdee_query_handler import (
    PreviewTdeeQueryHandler,
)
from src.app.queries.tdee import PreviewTdeeQuery


@pytest.mark.asyncio
async def test_preview_tdee_activity_multiplier_excludes_training_volume():
    handler = PreviewTdeeQueryHandler()

    result = await handler.handle(
        PreviewTdeeQuery(
            age=30,
            sex="male",
            height=180,
            weight=80,
            job_type="desk",
            training_days_per_week=6,
            training_minutes_per_session=90,
            goal="recomp",
            unit_system="metric",
        )
    )

    assert result["bmr"] == pytest.approx(1780.0, abs=0.1)
    assert result["tdee"] == pytest.approx(2136.0, abs=0.1)
    assert result["activity_multiplier"] == 1.2
    assert result["calculation_contract"] == "onboarding_preview_v2"
    assert result["macro_preset"] == "standard"
    assert result["target_revision"] == 0


@pytest.mark.asyncio
async def test_preview_tdee_custom_macros_derives_calories_from_macro_grams():
    handler = PreviewTdeeQueryHandler()

    result = await handler.handle(
        PreviewTdeeQuery(
            age=22,
            sex="male",
            height=170,
            weight=70,
            job_type="desk",
            training_days_per_week=4,
            training_minutes_per_session=52,
            training_level="intermediate",
            goal="recomp",
            diet_type="keto",
            custom_protein_g=101.04,
            custom_carbs_g=25.16,
            custom_fat_g=60.27,
            unit_system="metric",
        )
    )

    assert result["is_custom"] is True
    assert result["macro_preset"] == "keto"
    assert result["macros"] == {
        "protein": 101.0,
        "carbs": 25.2,
        "fat": 60.3,
        "calories": 1047.5,
    }


@pytest.mark.asyncio
async def test_preview_tdee_requested_calories_scales_macros_proportionally():
    handler = PreviewTdeeQueryHandler()

    result = await handler.handle(
        PreviewTdeeQuery(
            age=22,
            sex="male",
            height=170,
            weight=70,
            job_type="desk",
            training_days_per_week=4,
            training_minutes_per_session=52,
            training_level="intermediate",
            goal="recomp",
            requested_calories=2200,
            unit_system="metric",
        )
    )

    assert result["is_custom"] is False
    assert result["macro_preset"] == "standard"
    assert result["macros"]["calories"] == pytest.approx(2200, abs=2)

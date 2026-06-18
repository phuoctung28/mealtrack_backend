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

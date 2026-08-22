from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app.handlers.query_handlers.get_user_tdee_query_handler import (
    GetUserTdeeQueryHandler,
)
from src.app.queries.tdee import GetUserTdeeQuery
from src.domain.model.user import Goal, MacroPreset, MacroTargets, TdeeResponse


def _profile(**overrides):
    profile = MagicMock(
        age=30,
        gender="male",
        height_cm=180.0,
        weight_kg=80.0,
        job_type="desk",
        training_days_per_week=0,
        training_minutes_per_session=0,
        fitness_goal="recomp",
        body_fat_percentage=None,
        training_level=None,
        dietary_preferences=[],
        has_custom_macros=False,
        profile_target_revision=1,
    )
    for key, value in overrides.items():
        setattr(profile, key, value)
    return profile


def _tdee_response(macro_preset=MacroPreset.STANDARD):
    return TdeeResponse(
        bmr=1700.0,
        tdee=2100.0,
        goal=Goal.RECOMP,
        formula_used="Mifflin-St Jeor",
        macro_preset=macro_preset,
        macros=MacroTargets(
            calories=1900.0,
            protein=95.0,
            carbs=23.8,
            fat=158.3,
        ),
    )


@pytest.mark.asyncio
async def test_calculated_keto_response_derives_target_calories_from_returned_macros():
    profile = _profile(dietary_preferences=["keto"])
    query_result = MagicMock()
    query_result.scalars.return_value.first.return_value = profile
    uow = MagicMock()
    uow.session.execute = AsyncMock(return_value=query_result)
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    service = MagicMock(calculate_tdee=MagicMock(return_value=_tdee_response(MacroPreset.KETO)))
    handler = GetUserTdeeQueryHandler(tdee_service=service)

    with patch(
        "src.app.handlers.query_handlers.get_user_tdee_query_handler.AsyncUnitOfWork",
        return_value=uow,
    ):
        response = await handler._compute_tdee(GetUserTdeeQuery(user_id="user-1"))

    assert response["macro_preset"] == "keto"
    assert response["target_calories"] == 1899.9
    assert response["target_calories"] == response["macros"]["calories"]
    assert response["target_calories"] == (
        response["macros"]["protein"] * 4
        + response["macros"]["carbs"] * 4
        + response["macros"]["fat"] * 9
    )


def test_custom_response_derives_target_calories_from_returned_rounded_macros():
    profile = _profile(
        has_custom_macros=True,
        custom_protein_g=100.04,
        custom_carbs_g=123.46,
        custom_fat_g=50.04,
    )
    handler = GetUserTdeeQueryHandler(tdee_service=MagicMock(calculate_tdee=MagicMock(return_value=_tdee_response())))

    response = handler._build_custom_macros_response(
        GetUserTdeeQuery(user_id="user-1"), profile, MacroPreset.STANDARD
    )

    assert response["target_calories"] == 1344.0
    assert response["target_calories"] == response["macros"]["calories"]
    assert response["target_calories"] == (
        response["macros"]["protein"] * 4
        + response["macros"]["carbs"] * 4
        + response["macros"]["fat"] * 9
    )

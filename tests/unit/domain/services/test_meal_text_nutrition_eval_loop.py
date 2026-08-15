from types import SimpleNamespace

import pytest

from src.domain.services.meal_text_nutrition_eval_loop import (
    ParseTextEvalCase,
    ParseTextEvalObservation,
    ParseTextNutritionEvalLoop,
)


def _case(case_id: str = "en-potato-100g") -> ParseTextEvalCase:
    return ParseTextEvalCase(
        case_id=case_id,
        text="100g potato",
        language="en",
        expected_lookup_name="potato",
        expected_quantity_g=100,
        expected_source="fatsecret",
        expected_calorie_range=(60, 100),
        expected_candidate_id="potato",
    )


def _observation(source: str = "fatsecret", candidate: str | None = "potato"):
    item = SimpleNamespace(calories=77, data_source=source)
    return ParseTextEvalObservation(
        response=SimpleNamespace(items=[item]),
        extracted_lookup_name="potato",
        extracted_quantity_g=100,
        selected_candidate_id=candidate,
        provider_searches=1,
        provider_details=1,
        duration_ms=10,
    )


@pytest.mark.asyncio
async def test_eval_loop_reports_deterministic_metrics_and_passes_gates():
    loop = ParseTextNutritionEvalLoop()
    summary = await loop.evaluate([_case()], lambda _case: _ready(_observation()))

    assert summary.contract_pass_rate == 1.0
    assert summary.identity_quantity_pass_rate == 1.0
    assert summary.candidate_pass_rate == 1.0
    assert summary.common_reference_pass_rate == 1.0
    assert summary.catastrophic_outliers == 0
    assert summary.fallback_rate == 0.0
    assert summary.provider_search_calls == (1,)
    assert summary.provider_detail_calls == (1,)
    assert summary.latency_p95_ms == 10
    loop.enforce_gates(summary)


@pytest.mark.asyncio
async def test_eval_loop_marks_potato_calorie_outlier_as_gate_failure():
    loop = ParseTextNutritionEvalLoop()
    observation = _observation()
    observation = ParseTextEvalObservation(
        response=SimpleNamespace(
            items=[SimpleNamespace(calories=890, data_source="ai_estimate")]
        ),
        extracted_lookup_name=observation.extracted_lookup_name,
        extracted_quantity_g=observation.extracted_quantity_g,
        selected_candidate_id=observation.selected_candidate_id,
        provider_searches=observation.provider_searches,
        provider_details=observation.provider_details,
        duration_ms=observation.duration_ms,
    )
    summary = await loop.evaluate([_case()], lambda _case: _ready(observation))

    assert summary.catastrophic_outliers == 1
    with pytest.raises(ValueError, match="catastrophic_outliers"):
        loop.enforce_gates(summary)


async def _ready(observation):
    return observation

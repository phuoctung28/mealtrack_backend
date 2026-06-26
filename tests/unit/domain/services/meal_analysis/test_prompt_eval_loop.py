import pytest

from src.domain.services.meal_analysis.prompt_eval_loop import (
    PromptEvalCase,
    PromptEvalLoop,
    PromptEvalResult,
)


def _valid_payload() -> dict:
    return {
        "structured_data": {
            "dish_name": "Chicken Rice",
            "foods": [
                {
                    "name": "Chicken",
                    "quantity_g": 120,
                    "macros": {"protein_g": 30, "carbs_g": 0, "fat_g": 6},
                }
            ],
            "confidence": 0.9,
        }
    }


def _invalid_payload() -> dict:
    return {
        "structured_data": {"dish_name": "Broken", "foods": [{"name": "No macros"}]}
    }


def _legacy_alias_payload() -> dict:
    return {
        "structured_data": {
            "dish_name": "Legacy Chicken Rice",
            "foods": [
                {
                    "name": "Chicken",
                    "quantity": 120,
                    "unit": "g",
                    "macros": {"protein": 30, "carbs": 0, "fat": 6},
                }
            ],
            "confidence": 0.9,
        }
    }


def _legacy_alias_payload_without_unit() -> dict:
    return {
        "structured_data": {
            "dish_name": "Legacy Chicken Rice",
            "foods": [
                {
                    "name": "Chicken",
                    "quantity": 120,
                    "macros": {"protein": 30, "carbs": 0, "fat": 6},
                }
            ],
            "confidence": 0.9,
        }
    }


def test_rank_candidates_prefers_higher_parse_success_then_lower_token_cost():
    loop = PromptEvalLoop()
    cases = [
        PromptEvalCase(case_id="ok-1", response_payload=_valid_payload()),
        PromptEvalCase(case_id="ok-2", response_payload=_valid_payload()),
    ]
    candidates = {
        "long": "x" * 1200,
        "short": "x" * 200,
    }

    ranked = loop.rank_candidates(candidates, cases)

    assert ranked[0].name == "short"
    assert ranked[0].parse_success_rate == 1.0
    assert ranked[1].name == "long"


def test_rank_candidates_penalizes_parse_failures():
    loop = PromptEvalLoop()
    cases = [
        PromptEvalCase(case_id="ok", response_payload=_valid_payload()),
        PromptEvalCase(case_id="bad", response_payload=_invalid_payload()),
    ]
    candidates = {
        "candidate-a": "x" * 250,
        "candidate-b": "x" * 250,
    }

    ranked = loop.rank_candidates(
        candidates,
        cases,
        case_overrides={
            "candidate-a": {"bad": _valid_payload()},
        },
    )

    assert ranked[0].name == "candidate-a"
    assert ranked[0].parse_success_rate == 1.0
    assert ranked[1].parse_success_rate == 0.5


def test_enforce_thresholds_raises_on_regression():
    loop = PromptEvalLoop()
    cases = [PromptEvalCase(case_id="bad", response_payload=_invalid_payload())]
    candidates = {"candidate": "x" * 300}
    result = loop.rank_candidates(candidates, cases)[0]

    try:
        loop.enforce_thresholds(
            result, min_parse_success_rate=0.9, max_prompt_tokens=100
        )
        raise AssertionError("Expected threshold validation to fail")
    except ValueError as exc:
        message = str(exc)
        assert "parse_success_rate" in message or "prompt_tokens_estimate" in message


def test_schema_invalid_payload_has_lower_validation_rate():
    """Candidate with validation-failing payloads scores lower validation_success_rate."""
    loop = PromptEvalLoop()
    invalid_quantity_payload = {
        "structured_data": {
            "dish_name": "Broken",
            "foods": [
                {
                    "name": "Huge",
                    "quantity_g": 150000,
                    "macros": {"protein_g": 500, "carbs_g": 1000, "fat_g": 200},
                }
            ],
        }
    }
    cases = [
        PromptEvalCase(case_id="valid", response_payload=_valid_payload()),
        PromptEvalCase(case_id="invalid", response_payload=invalid_quantity_payload),
    ]
    candidates = {"candidate": "x" * 200}
    ranked = loop.rank_candidates(candidates, cases)
    assert ranked[0].validation_success_rate == pytest.approx(0.5)


def test_alias_only_legacy_payload_lowers_validation_rate():
    """Prompt validation must match parser preflight rejection for legacy aliases."""
    loop = PromptEvalLoop()
    cases = [
        PromptEvalCase(case_id="valid", response_payload=_valid_payload()),
        PromptEvalCase(case_id="legacy", response_payload=_legacy_alias_payload()),
    ]
    candidates = {"candidate": "x" * 200}

    ranked = loop.rank_candidates(candidates, cases)

    assert ranked[0].parse_success_rate == pytest.approx(0.5)
    assert ranked[0].validation_success_rate == pytest.approx(0.5)


def test_alias_only_legacy_payload_without_unit_lowers_validation_rate():
    """Prompt validation must reject alias-only payloads accepted by schema aliases."""
    loop = PromptEvalLoop()
    cases = [
        PromptEvalCase(case_id="valid", response_payload=_valid_payload()),
        PromptEvalCase(
            case_id="legacy",
            response_payload=_legacy_alias_payload_without_unit(),
        ),
    ]
    candidates = {"candidate": "x" * 200}

    ranked = loop.rank_candidates(candidates, cases)

    assert ranked[0].parse_success_rate == pytest.approx(0.5)
    assert ranked[0].validation_success_rate == pytest.approx(0.5)


def test_enforce_thresholds_fails_on_validation_rate():
    """enforce_thresholds raises when validation_success_rate below threshold."""
    loop = PromptEvalLoop()
    result = PromptEvalResult(
        name="candidate",
        parse_success_rate=1.0,
        validation_success_rate=0.4,
        prompt_tokens_estimate=100.0,
        score=100.0,
    )
    with pytest.raises(ValueError, match="validation_success_rate"):
        loop.enforce_thresholds(
            result,
            min_parse_success_rate=0.5,
            max_prompt_tokens=200,
            min_validation_success_rate=0.8,
        )


def test_valid_payload_achieves_full_validation_rate():
    """All-valid cases yield validation_success_rate=1.0."""
    loop = PromptEvalLoop()
    cases = [
        PromptEvalCase(case_id="ok1", response_payload=_valid_payload()),
        PromptEvalCase(case_id="ok2", response_payload=_valid_payload()),
    ]
    candidates = {"candidate": "x" * 200}
    ranked = loop.rank_candidates(candidates, cases)
    assert ranked[0].validation_success_rate == pytest.approx(1.0)

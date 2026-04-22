from src.domain.services.meal_analysis.prompt_eval_loop import (
    PromptEvalCase,
    PromptEvalLoop,
)


def _valid_payload() -> dict:
    return {
        "structured_data": {
            "dish_name": "Chicken Rice",
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


def _invalid_payload() -> dict:
    return {"structured_data": {"dish_name": "Broken", "foods": [{"name": "No macros"}]}}


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
        loop.enforce_thresholds(result, min_parse_success_rate=0.9, max_prompt_tokens=100)
        assert False, "Expected threshold validation to fail"
    except ValueError as exc:
        message = str(exc)
        assert "parse_success_rate" in message or "prompt_tokens_estimate" in message

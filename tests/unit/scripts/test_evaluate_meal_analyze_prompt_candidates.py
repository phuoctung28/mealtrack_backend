import importlib.util
from pathlib import Path

from src.domain.services.meal_analysis.prompt_eval_loop import PromptEvalResult


def _load_module():
    script_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "development"
        / "evaluate_meal_analyze_prompt_candidates.py"
    )
    spec = importlib.util.spec_from_file_location("evaluate_meal_analyze", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_resolve_gate_candidate_prefers_runtime_selected_candidate():
    module = _load_module()
    ranked = [
        PromptEvalResult(
            name="legacy",
            parse_success_rate=1.0,
            prompt_tokens_estimate=180.0,
            score=98.2,
        ),
        PromptEvalResult(
            name="optimized",
            parse_success_rate=1.0,
            prompt_tokens_estimate=220.0,
            score=97.8,
        ),
    ]

    chosen = module.resolve_gate_candidate(ranked, runtime_candidate_name="optimized")

    assert chosen.name == "optimized"

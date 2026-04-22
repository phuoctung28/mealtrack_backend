#!/usr/bin/env python3
"""Evaluate and rank meal analyze prompt candidates with parser-based scoring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.services.meal_analysis.prompt_eval_loop import PromptEvalCase, PromptEvalLoop
from src.domain.strategies.meal_analysis_strategy import BasicAnalysisStrategy
from src.infra.config.settings import get_settings


def _default_cases() -> list[PromptEvalCase]:
    return [
        PromptEvalCase(
            case_id="single-food",
            response_payload={
                "structured_data": {
                    "dish_name": "Chicken Breast",
                    "foods": [
                        {
                            "name": "Chicken Breast",
                            "quantity": 150,
                            "unit": "g",
                            "macros": {"protein": 45, "carbs": 0, "fat": 5},
                        }
                    ],
                    "confidence": 0.9,
                }
            },
        ),
        PromptEvalCase(
            case_id="multi-food",
            response_payload={
                "structured_data": {
                    "dish_name": "Rice Bowl",
                    "foods": [
                        {
                            "name": "Rice",
                            "quantity": 200,
                            "unit": "g",
                            "macros": {"protein": 4, "carbs": 56, "fat": 1},
                        },
                        {
                            "name": "Egg",
                            "quantity": 50,
                            "unit": "g",
                            "macros": {"protein": 6, "carbs": 1, "fat": 5},
                        },
                    ],
                    "confidence": 0.84,
                }
            },
        ),
    ]


def resolve_gate_candidate(ranked: list, runtime_candidate_name: str):
    for candidate in ranked:
        if candidate.name == runtime_candidate_name:
            return candidate
    return ranked[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-parse-success-rate", type=float, default=1.0)
    parser.add_argument("--max-prompt-tokens", type=float, default=700.0)
    args = parser.parse_args()

    loop = PromptEvalLoop()
    cases = _default_cases()
    candidates = {
        "optimized": BasicAnalysisStrategy(optimized_prompt_enabled=True).get_analysis_prompt(),
        "legacy": BasicAnalysisStrategy(optimized_prompt_enabled=False).get_analysis_prompt(),
    }

    ranked = loop.rank_candidates(candidates, cases)
    runtime_candidate_name = (
        "optimized"
        if get_settings().MEAL_ANALYZE_OPTIMIZED_PROMPT_ENABLED
        else "legacy"
    )
    candidate_for_gate = resolve_gate_candidate(
        ranked, runtime_candidate_name=runtime_candidate_name
    )

    print(json.dumps([result.__dict__ for result in ranked], indent=2))

    try:
        loop.enforce_thresholds(
            candidate_for_gate,
            min_parse_success_rate=args.min_parse_success_rate,
            max_prompt_tokens=args.max_prompt_tokens,
        )
    except ValueError as exc:
        print(f"Prompt eval regression gate failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

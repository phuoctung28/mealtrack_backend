from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from src.domain.parsers.gpt_response_parser import (
    GPTResponseParser,
    GPTResponseParsingError,
)
from src.domain.parsers.vision_response_models import VisionAnalyzeResponse


@dataclass(frozen=True)
class PromptEvalCase:
    case_id: str
    response_payload: dict


@dataclass(frozen=True)
class PromptEvalResult:
    name: str
    parse_success_rate: float
    validation_success_rate: float
    prompt_tokens_estimate: float
    score: float


class PromptEvalLoop:
    """Offline evaluator for ranking prompt candidates with parser fidelity and cost."""

    def __init__(self, parser: GPTResponseParser | None = None):
        self._parser = parser or GPTResponseParser()

    def rank_candidates(
        self,
        candidates: dict[str, str],
        cases: list[PromptEvalCase],
        case_overrides: dict[str, dict[str, dict]] | None = None,
    ) -> list[PromptEvalResult]:
        if not cases:
            raise ValueError("cases must not be empty")

        ranked: list[PromptEvalResult] = []
        overrides = case_overrides or {}

        for name, prompt in candidates.items():
            success_count = 0
            validation_success_count = 0
            candidate_overrides = overrides.get(name, {})

            for case in cases:
                payload = candidate_overrides.get(case.case_id, case.response_payload)
                structured = payload.get("structured_data", {})

                try:
                    VisionAnalyzeResponse.model_validate(structured)
                    validation_success_count += 1
                except ValidationError:
                    pass

                try:
                    self._parser.parse_to_nutrition(payload)
                    success_count += 1
                except GPTResponseParsingError:
                    pass

            parse_success_rate = success_count / len(cases)
            validation_success_rate = validation_success_count / len(cases)
            prompt_tokens_estimate = len(prompt) / 4.0
            score = (parse_success_rate * 100.0) - (prompt_tokens_estimate / 100.0)

            ranked.append(
                PromptEvalResult(
                    name=name,
                    parse_success_rate=parse_success_rate,
                    validation_success_rate=validation_success_rate,
                    prompt_tokens_estimate=prompt_tokens_estimate,
                    score=score,
                )
            )

        return sorted(
            ranked,
            key=lambda item: (item.parse_success_rate, -item.prompt_tokens_estimate),
            reverse=True,
        )

    def enforce_thresholds(
        self,
        result: PromptEvalResult,
        min_parse_success_rate: float,
        max_prompt_tokens: float,
        min_validation_success_rate: float = 0.0,
    ) -> None:
        failures: list[str] = []
        if result.parse_success_rate < min_parse_success_rate:
            failures.append(
                f"parse_success_rate={result.parse_success_rate:.3f} < {min_parse_success_rate:.3f}"
            )
        if result.validation_success_rate < min_validation_success_rate:
            failures.append(
                f"validation_success_rate={result.validation_success_rate:.3f} < {min_validation_success_rate:.3f}"
            )
        if result.prompt_tokens_estimate > max_prompt_tokens:
            failures.append(
                f"prompt_tokens_estimate={result.prompt_tokens_estimate:.1f} > {max_prompt_tokens:.1f}"
            )
        if failures:
            raise ValueError("; ".join(failures))

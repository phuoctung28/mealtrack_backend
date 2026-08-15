"""Deterministic quality gates for parse-text nutrition resolution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from statistics import median
from typing import Any

COMMON_REFERENCE_SOURCES = {"usda", "fatsecret"}


@dataclass(frozen=True)
class ParseTextEvalCase:
    case_id: str
    text: str
    language: str
    expected_lookup_name: str
    expected_quantity_g: float
    expected_source: str
    expected_calorie_range: tuple[float, float]
    expected_candidate_id: str | None = None
    ai_payload: dict[str, Any] = field(default_factory=dict)
    provider_candidates: list[dict[str, Any]] = field(default_factory=list)
    provider_details: dict[str, dict[str, Any]] = field(default_factory=dict)
    local_reference: dict[str, Any] | None = None


@dataclass(frozen=True)
class ParseTextEvalObservation:
    response: Any
    extracted_lookup_name: str | None
    extracted_quantity_g: float | None
    selected_candidate_id: str | None
    provider_searches: int
    provider_details: int
    duration_ms: float


@dataclass(frozen=True)
class ParseTextEvalCaseResult:
    case_id: str
    contract_pass: bool
    identity_pass: bool
    quantity_pass: bool
    candidate_pass: bool
    reference_pass: bool
    catastrophic_outlier: bool
    source: str | None
    provider_calls: int
    duration_ms: float
    reason_codes: tuple[str, ...] = ()
    provider_search_calls: int = 0
    provider_detail_calls: int = 0
    fallback_used: bool = False


@dataclass(frozen=True)
class ParseTextEvalSummary:
    case_count: int
    contract_pass_rate: float
    identity_quantity_pass_rate: float
    candidate_pass_rate: float
    common_reference_pass_rate: float
    catastrophic_outliers: int
    invalid_reference_accepts: int
    provider_calls: tuple[int, ...]
    latency_p50_ms: float
    latency_p95_ms: float
    cases: tuple[ParseTextEvalCaseResult, ...]
    fallback_rate: float = 0.0
    provider_search_calls: tuple[int, ...] = ()
    provider_detail_calls: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


EvalRunner = Callable[[ParseTextEvalCase], Awaitable[ParseTextEvalObservation]]


class ParseTextNutritionEvalLoop:
    """Run cases and evaluate only low-cardinality, non-PII observations."""

    async def evaluate(
        self, cases: list[ParseTextEvalCase], runner: EvalRunner
    ) -> ParseTextEvalSummary:
        if not cases:
            raise ValueError("evaluation corpus must not be empty")
        results = [self._evaluate_case(case, await runner(case)) for case in cases]
        latencies = [result.duration_ms for result in results]
        common_results = [
            result
            for case, result in zip(cases, results, strict=True)
            if case.expected_source in COMMON_REFERENCE_SOURCES
        ]
        return ParseTextEvalSummary(
            case_count=len(results),
            contract_pass_rate=_rate(results, "contract_pass"),
            identity_quantity_pass_rate=sum(
                result.identity_pass and result.quantity_pass for result in results
            )
            / len(results),
            candidate_pass_rate=_rate(results, "candidate_pass"),
            common_reference_pass_rate=(
                _rate(common_results, "reference_pass") if common_results else 1.0
            ),
            catastrophic_outliers=sum(
                result.catastrophic_outlier for result in results
            ),
            invalid_reference_accepts=sum(
                result.source == "fatsecret" and not result.reference_pass
                for result in results
            ),
            provider_calls=tuple(result.provider_calls for result in results),
            latency_p50_ms=round(median(latencies), 3),
            latency_p95_ms=round(_percentile(latencies, 0.95), 3),
            cases=tuple(results),
            fallback_rate=_rate(results, "fallback_used"),
            provider_search_calls=tuple(
                result.provider_search_calls for result in results
            ),
            provider_detail_calls=tuple(
                result.provider_detail_calls for result in results
            ),
        )

    @staticmethod
    def enforce_gates(summary: ParseTextEvalSummary) -> None:
        failures: list[str] = []
        gates = (
            (summary.contract_pass_rate == 1.0, "contract_pass_rate"),
            (summary.catastrophic_outliers == 0, "catastrophic_outliers"),
            (
                summary.identity_quantity_pass_rate >= 0.95,
                "identity_quantity_pass_rate",
            ),
            (summary.candidate_pass_rate >= 0.95, "candidate_pass_rate"),
            (summary.common_reference_pass_rate >= 0.90, "common_reference_pass_rate"),
            (summary.invalid_reference_accepts == 0, "invalid_reference_accepts"),
        )
        failures.extend(name for passed, name in gates if not passed)
        if failures:
            raise ValueError(
                "parse-text evaluation gates failed: " + ", ".join(failures)
            )

    @staticmethod
    def _evaluate_case(
        case: ParseTextEvalCase, observation: ParseTextEvalObservation
    ) -> ParseTextEvalCaseResult:
        item = getattr(observation.response, "items", [None])[0]
        source = getattr(item, "data_source", None)
        calories = float(getattr(item, "calories", 0.0) or 0.0)
        identity_pass = observation.extracted_lookup_name == case.expected_lookup_name
        quantity_pass = observation.extracted_quantity_g == case.expected_quantity_g
        candidate_pass = (
            case.expected_candidate_id is None
            or observation.selected_candidate_id == case.expected_candidate_id
        )
        reference_pass = source == case.expected_source
        contract_pass = item is not None and isinstance(source, str)
        low, high = case.expected_calorie_range
        catastrophic = not low <= calories <= high
        reasons = tuple(
            name
            for passed, name in (
                (identity_pass, "identity"),
                (quantity_pass, "quantity"),
                (candidate_pass, "candidate"),
                (reference_pass, "source"),
                (not catastrophic, "calorie_outlier"),
            )
            if not passed
        )
        return ParseTextEvalCaseResult(
            case_id=case.case_id,
            contract_pass=contract_pass,
            identity_pass=identity_pass,
            quantity_pass=quantity_pass,
            candidate_pass=candidate_pass,
            reference_pass=reference_pass,
            catastrophic_outlier=catastrophic,
            source=source,
            provider_calls=observation.provider_searches + observation.provider_details,
            duration_ms=observation.duration_ms,
            reason_codes=reasons,
            provider_search_calls=observation.provider_searches,
            provider_detail_calls=observation.provider_details,
            fallback_used=source == "ai_estimate",
        )


def _rate(results: list[ParseTextEvalCaseResult], field: str) -> float:
    return sum(bool(getattr(result, field)) for result in results) / len(results)


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return ordered[index]

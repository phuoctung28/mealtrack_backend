---
phase: 3
title: "Retry Budget and Failure Classification"
status: pending
priority: P1
effort: "1 day"
dependencies: [2]
---

# Phase 3: Retry Budget and Failure Classification

## Overview

Replace blind whole-chain retries with failure-kind aware retry and fallback behavior. The current analyzer can retry the entire vision path, while `AIModelManager` also walks a provider chain. That can turn malformed JSON or schema drift into 30-38s user-visible failures.

## Context Links

- `src/infra/adapters/ai_json_utils.py`
- `tests/unit/infra/adapters/test_ai_json_logging.py`
- `src/infra/services/ai/ai_model_manager.py`
- `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- `src/domain/services/meal_analysis/fast_path_policy.py`
- `src/infra/services/ai/gemini_model_manager.py`
- `src/infra/config/settings.py`
- `docs/code-standards.md`

## Key Insights

- Production logs show long 503s around 31-38s and occasional 200s around 24s.
- `MEAL_ANALYZE_MAX_ATTEMPTS` retries the whole image analysis flow by default.
- Provider fallback already tries multiple models. Outer retry should not repeat every provider for non-transient parse/schema failures.
- Circuit breaker may not trip on parse failures when provider `extract_error_code()` returns no tripping code.

## Requirements

- Functional: classify failures as transient provider, timeout, rate limit, schema validation, JSON parse, no-food/low-confidence, or unknown.
- Functional: retry transient/provider failures when budget remains.
- Functional: do not retry the full chain for deterministic schema/parse failures from the same provider/model.
- Functional: fallback to the next provider/model on schema/parse failure when another candidate remains.
- Non-functional: enforce a bounded request wall-time target for image analysis.
- Non-functional: preserve existing public API error semantics unless a current status mapping is clearly wrong.

## Architecture

Add a small failure classification boundary in infrastructure/application code, not domain entities. Provider adapters raise or return classified failures. `AIModelManager` uses classification to decide provider fallback and circuit-breaker recording. The upload handler uses classification and remaining time budget to decide whether an outer retry is worthwhile.

Suggested behavior:

| Failure kind | Same provider retry | Next provider fallback | Outer retry |
|--------------|---------------------|------------------------|-------------|
| timeout | no, unless budget remains | yes | maybe |
| 429/5xx | no immediate same-model retry | yes | maybe |
| schema validation | no | yes | no |
| JSON parse | no | yes | no |
| no food detected | no | no | no |
| unknown | no | yes if available | no by default |

## Related Code Files

- Modify: `src/infra/services/ai/ai_model_manager.py`
- Modify: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Modify: `src/infra/services/ai/providers/gemini_provider.py`
- Modify: `src/infra/services/ai/providers/cloudflare_workers_ai_provider.py`
- Modify: `src/infra/adapters/ai_json_utils.py`
- Modify: `tests/unit/infra/services/ai/test_ai_model_manager.py`
- Modify: `tests/unit/app/handlers/command_handlers/test_upload_meal_image_immediately_command_handler.py`

## Implementation Steps

### Tests Before

1. Add manager test: schema/parse failure on Cloudflare falls through to Gemini without retrying Cloudflare.
2. Add manager test: timeout/rate-limit failure records circuit breaker signal and falls through.
3. Add handler test: parse/schema failure does not run the whole chain twice.
4. Add handler test: transient timeout can retry only when remaining request budget is enough.
5. Add handler test: final user-facing error maps to existing 503/analysis-unavailable path.

### Refactor

1. Define or reuse a small classified AI exception/result type with `kind`, `provider`, `model`, and safe `error_code`.
2. Map provider exceptions and parser/schema exceptions to the classification.
3. Update `AIModelManager.generate_with_vision()` to use classification for fallback and circuit-breaker decisions.
4. Update upload handler outer retry to check classification and remaining wall-time budget.
5. Keep `ai_json_utils.extract_json()` as the only raw text parser.
6. Avoid adding sleeps/backoff that push image scans past current user tolerance.

### Tests After

1. Run model-manager tests.
2. Run upload handler tests.
3. Run provider tests.
4. Run parser logging tests.

## Success Criteria

- [ ] Parse/schema failures do not trigger full-chain outer retry.
- [ ] Transient failures can still fall back or retry within a clear budget.
- [ ] Circuit-breaker metrics/failures include parse/schema failures when they affect provider reliability.
- [ ] Long 503 behavior has a concrete maximum attempt/time budget.
- [ ] Focused tests pass.

## Risk Assessment

Risk: reducing retries lowers occasional recovery rate. Mitigation: only remove retries for deterministic parse/schema/no-food failures; transient failures still use fallback/retry budget.

Risk: too many new exception types. Mitigation: keep classification small and local to AI infrastructure/application handling.

## Security Considerations

Never log raw AI content, image bytes, base64, signed URLs, prompt text, Firebase claims, or user food descriptions.

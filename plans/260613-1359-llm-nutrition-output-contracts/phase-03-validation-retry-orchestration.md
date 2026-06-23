---
phase: 3
title: "Validation Retry Orchestration"
status: completed
effort: "1d"
---

# Phase 3: Validation Retry Orchestration

## Context Links

- Vision adapter: `src/infra/adapters/vision_ai_service.py`
- Text parse handler: `src/app/handlers/command_handlers/parse_meal_text_handler.py`
- Meal generation adapter: `src/infra/adapters/meal_generation_service.py`
- AI exceptions: `src/domain/exceptions/ai_exceptions.py`
- Prompt definitions: `src/domain/services/prompts/system_prompts.py`
- Vision tests: `tests/unit/infra/adapters/test_vision_ai_service.py`
- Text handler tests: `tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py`

## Overview

Add the user-preserving behavior: invalid AI output gets one automatic repair
attempt, then a controlled failure. This is the core difference between a
well-designed LLM boundary and the current parser workaround.

Priority: P1.

## Requirements

- Distinguish provider outages from invalid AI output.
- Retry invalid structured output exactly once.
- Retry prompt includes compact correction context:
  - field path or validation summary.
  - instruction to return the full corrected response.
  - no raw image bytes, no full base64, no oversized payload logging.
- Retry success follows normal UX.
- Retry failure raises a controlled application/domain exception.
- Do not retry:
  - circuit-breaker provider outage already handled by fallback chain.
  - low confidence alone.
  - FatSecret lookup mismatch.
- Add semantic validation beyond Pydantic:
  - realistic quantity bounds by contract.
  - item count.
  - non-negative macros.
  - optional macro-vs-quantity sanity where local rules exist.

## Architecture

Use a small shared validation/retry helper only if it removes duplication
between image and text flows. Otherwise keep retry orchestration near the AI call
site for readability:

- Vision: `VisionAIService.analyze_with_strategy`.
- Text: `ParseMealTextHandler.handle` or a focused private method around
  `MealGenerationService.generate_meal_plan_async`.

Recommended exception:

- `AIOutputValidationError` in `src/domain/exceptions/ai_exceptions.py`
  carrying purpose, attempt count, and sanitized validation details.

## Related Code Files

Modify:

- `src/domain/exceptions/ai_exceptions.py`
- `src/infra/adapters/vision_ai_service.py`
- `src/app/handlers/command_handlers/parse_meal_text_handler.py`
- `src/infra/adapters/meal_generation_service.py` if schema plumbing is needed
- `src/domain/services/prompts/system_prompts.py`
- `tests/unit/infra/adapters/test_vision_ai_service.py`
- `tests/unit/infra/adapters/test_vision_ai_service_resilience.py`
- `tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py`

Create if needed:

- `src/domain/services/ai_output_validation_service.py`
- `tests/unit/domain/services/test_ai_output_validation_service.py`

## Implementation Steps

1. [x] Write failing vision service tests:
   - first structured output invalid, retry valid, method returns normal payload.
   - first and retry both invalid, method raises `AIOutputValidationError`.
   - provider `AIUnavailableError` still propagates without validation retry.
2. [x] Write failing text parse tests:
   - invalid AI text parse output retries once.
   - retry success preserves current DTO behavior.
   - retry failure maps to controlled error behavior expected by routes/tests.
3. [x] Add `AIOutputValidationError` with sanitized detail fields.
4. [x] Add validation detail summarizer for Pydantic/semantic errors.
5. [x] Implement retry loop in vision path using `schema=VisionNutritionResponse`.
6. [x] Implement text schema call using `schema=MealTextNutritionResponse`.
7. [x] Add correction-prompt helper that appends validation detail to existing
   prompt without replacing the system prompt.
8. [x] Ensure logs include purpose, strategy/model if available, and attempt count.
9. [x] Run focused service and handler tests.

## Implementation Notes

- Added `AIOutputValidationError` and shared validation helpers for sanitized
  details and retry prompt context.
- Image meal analysis uses `VisionNutritionResponse` and retries invalid
  structured output exactly once.
- Ingredient recognition keeps its existing unstructured `{name, confidence,
  category}` contract and does not receive the meal nutrition schema.
- Text parsing uses `MealTextNutritionResponse`, retries invalid structured
  output exactly once, and maps validated macros back to the existing DTO shape.
- FatSecret divergence checks now compare against backend-derived macro
  calories, not AI-reported calorie extras.
- API exception mapping returns friendly `AI_OUTPUT_INVALID` guidance without
  leaking field-level validation details.

## Success Criteria

- [x] Invalid vision output triggers exactly one retry.
- [x] Invalid text parse output triggers exactly one retry.
- [x] Retry success returns the same user-facing success shape as today.
- [x] Retry failure raises/mapping is controlled; raw parser/domain exception does not leak.
- [x] Provider outage fallback behavior is unchanged.
- [x] Logs are useful and sanitized.

## Verification

- `uv run pytest tests/unit/infra/adapters/test_vision_ai_service_resilience.py tests/unit/handlers/command_handlers/test_recognize_ingredient_command_handler.py tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py -q`
  - Result: 21 passed.
- `uv run pytest tests/unit/api/test_exceptions_unexpected.py tests/unit/domain/exceptions/test_ai_exceptions.py tests/unit/domain/services/test_ai_output_validation_service.py tests/unit/domain/model/ai/test_nutrition_contracts.py tests/unit/domain/parsers/test_gpt_response_parser.py tests/unit/domain/parsers/test_vision_response_models.py tests/unit/domain/ports/test_ai_provider_port.py tests/unit/infra/adapters/test_vision_ai_service.py tests/unit/infra/adapters/test_vision_ai_service_resilience.py tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py tests/unit/handlers/command_handlers/test_recognize_ingredient_command_handler.py tests/unit/infra/services/ai/test_ai_model_manager.py tests/unit/infra/services/ai/providers/test_gemini_provider.py tests/unit/infra/services/ai/test_schemas.py -q`
  - Result: 155 passed.
- Touched-file `ruff check`, `mypy`, `black --check`, and `py_compile`
  passed.

## Risk Assessment

- Risk: Retry adds latency. Mitigation: retry only invalid structured output,
  never every scan.
- Risk: Error handling conflates invalid output with provider outage. Mitigation:
  separate exception types and tests for both paths.
- Risk: Repeating same bad output. Mitigation: include field-specific correction
  detail and cap retries at one.

## Security Considerations

- No raw images or full user meal text in validation logs.
- Avoid returning internal validation detail directly to clients; use friendly
  API guidance.

## Next Steps

Proceed to Phase 4 after image and text retry behavior is covered by tests.

---
phase: 1
title: "Characterize Parse-Text Nutrition Contracts"
status: completed
effort: "1-2 days"
---

# Phase 1: Characterize Parse-Text Nutrition Contracts

## Overview

Lock the current authenticated/guest API shape, backend calorie derivation,
schema retry behavior, and fallback semantics before changing resolution. Add
failing tests for the known semantic gaps; do not change runtime behavior here.

**Priority:** P1
**Depends on:** none
**Produces:** a red test boundary for Phase 2

## Context Links

- [Approved design](../reports/260814-1023-parse-text-fatsecret-validation-harness.md)
- [Code-path research](../reports/260814-1030-parse-text-codepath-tdd-research.md)
- `src/api/routes/v1/meals_manual_text.py`
- `src/api/routes/v1/meals_route_helpers.py`
- `src/app/handlers/command_handlers/parse_meal_text_handler.py`
- `src/domain/model/ai/nutrition_contracts.py`

## Key Insights

- Both routes send `ParseMealTextCommand` through the same handler.
- `ParsedFoodItem` remains the public DTO; calories are derived from macros in
  route mapping, so arithmetic is correct even when model macros are absurd.
- The current handler selects FatSecret result zero, parses description text,
  and silently returns AI macros on any lookup error.
- Existing tests monkeypatch parsing/scaling and therefore miss the structured
  candidate/detail path.

## Requirements

- Preserve every current public response field and status mapping.
- Preserve one validation retry for malformed AI structured output.
- Characterize provider miss/timeout as non-retryable provider fallback.
- Add failing cases for wrong-first candidate, incomplete structured macros,
  truthful `data_source`, a single selected detail request, and the 890-kcal
  potato sentinel.
- Lock fiber/sugar propagation through the app DTO and public mapper, including
  fiber-aware backend calorie derivation for both routes.
- Lock one request-wide budget: at most two total AI generations, five FatSecret
  searches, five details, concurrency three, and one three-second external
  resolution deadline. Provider outage alone never consumes an AI retry.
- Add refinement-input tests for oversized/nested `current_items`, prompt
  injection in nested fields, and rejection before any AI/provider call.
- Keep tests hermetic: no network, secrets, live provider, or production data.

## Architecture And Data Flow

```text
auth route ---------\
                     -> ParseMealTextCommand -> ParseMealTextHandler -> DTO mapper
guest-trial route --/                              |
                                                   -> derived calories
```

The route/schema assertions stay green. New resolver assertions intentionally
fail against the current blind-first-result/description-parser implementation.

## Related Code Files

Modify:

- `tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py`
- `tests/unit/api/test_guest_parse_trial.py`
- `tests/unit/api/test_routes_with_mocked_event_bus.py`
- `tests/unit/domain/test_calorie_formula_parity.py`
- `tests/unit/domain/services/test_nutrition_resolver.py`
- `tests/unit/api/test_event_bus_dependency_singletons.py`

No production files change in this phase.

## Implementation Steps

1. **Tests Before:** snapshot the authenticated and guest response keys, totals,
   source string, units, and controlled `AI_OUTPUT_INVALID` 422 mapping.
2. Extend handler characterization for exactly one schema-validation retry and
   zero extra AI retries on provider outage.
3. Add a fixture that supplies structured FatSecret macros without a usable
   description; assert the current implementation fails to consume it.
4. Give the current handler fake both legacy and staged provider methods. Add a
   wrong-first/generic-second case and assert the observable desired behavior:
   staged search plus exactly one detail call. It remains red because the live
   handler calls only the legacy enriched search path today.
5. Add invalid macro mass, provider-energy mismatch, and missing required-field
   cases; assert none may claim `data_source="fatsecret"`.
6. Add `100gr khoai tay` with `quantity_g=100` and an AI 890-kcal macro payload;
   assert reference macros win, or unresolved unsafe fallback raises the
   existing controlled validation error.
7. Add combined-state tests: schema repair then unsafe fallback stops at two AI
   calls; provider deadline/call-budget exhaustion uses deterministic input
   order, cancels unfinished work, and never launches per-item AI retries.
8. Add public-route fixtures with non-zero fiber/sugar and assert the handler
   DTO, mapper, calories, and authenticated/guest JSON agree.
9. Add nested refinement size/injection and canary-log tests across sanitizer,
   handler, provider failure, and controlled 422 paths.
10. **Refactor:** test helpers/fakes only. Give the fake staged provider explicit
   search/detail counters; do not monkeypatch production parsing functions.
11. **Tests After:** run green characterization tests separately from the named
   expected-red semantic tests and record the red reasons in test docstrings.
12. **Regression Gate:** ensure no unrelated unit test is weakened or deleted.

Targeted commands:

```bash
pytest tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py -v
pytest tests/unit/api/test_guest_parse_trial.py tests/unit/api/test_routes_with_mocked_event_bus.py -v
pytest tests/unit/domain/test_calorie_formula_parity.py tests/unit/domain/services/test_nutrition_resolver.py -v
```

## Todo List

- [x] Lock authenticated and guest API contracts.
- [x] Lock retry, timeout, and 422 behavior.
- [x] Replace monkeypatched FatSecret test with staged provider fake.
- [x] Add all semantic red tests including potato 890.
- [x] Lock request-wide budgets and refinement rejection.
- [x] Lock fiber/sugar and public calorie parity.
- [x] Record exact expected-red failures for Phase 2.

## Success Criteria

- [x] Existing compatibility tests stay green.
- [x] New semantic tests fail for the intended current-code reasons only.
- [x] Tests prove calories are derived from macros, never accepted as provider
  or AI totals.
- [x] No production file, API schema, route, DB, or mobile contract changes.

## Risk Assessment

- **Brittle route snapshots:** assert the documented field contract, not JSON
  formatting or ordering.
- **False TDD green:** prohibit fake behavior that duplicates the desired
  implementation inside the test.
- **Dirty worktree:** restrict this phase to the listed tests and preserve all
  unrelated edits.

## Security And Privacy

- Test strings are versioned synthetic food descriptions, never user records.
- Fakes must not read environment credentials or attempt network calls.

## Next Steps

Phase 2 may start only after characterization is green and each semantic test is
confirmed red against the current runtime path.

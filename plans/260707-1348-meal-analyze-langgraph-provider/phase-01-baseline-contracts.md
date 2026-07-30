---
phase: 1
title: "Baseline Contracts"
status: completed
priority: P1
effort: "0.5-1d"
dependencies: []
---

# Phase 1: Baseline Contracts

## Context Links

- Brainstorm: `plans/reports/260707-1342-meal-analyze-langgraph-provider-brainstorm.md`
- Direct upload route: `src/api/routes/v1/meals.py`
- Scan-by-url route: `src/api/routes/v1/meal_scan_by_url.py`
- Direct upload handler: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Scan-by-url handler: `src/app/handlers/command_handlers/scan_by_url_command_handler.py`
- Parser contract: `src/domain/parsers/vision_response_parser.py`
- Vision schema: `src/domain/model/ai/nutrition_contracts.py`

## Overview

Lock existing behavior before introducing LangGraph. This phase adds regression
tests and architecture assertions only; production behavior should not change.

## Key Insights

- Current image analyze is synchronous READY response.
- Direct upload and scan-by-url have parallel persistence logic.
- Food-label scan intentionally has a different parser and metadata contract.
- Meal status enum does not support `READY_WITH_WARNINGS`.

## Requirements

- Functional: valid direct upload still persists READY scanner meal.
- Functional: valid meal scan-by-url still persists READY scanner meal.
- Functional: valid food-label scan-by-url still persists READY food-label meal.
- Functional: no-food images still stop before persistence.
- Non-functional: tests must run without real OpenAI, Cloudflare, FatSecret, Cloudinary, or DeepL calls.
- Non-functional: no schema or public response changes.

## Architecture

```text
tests
  -> mock image store / mock vision service
  -> current handlers
  -> fake async UoW
  -> assert meal fields and side effects
```

Regression tests become the safety net for later extraction into
`MealAnalyzeWorkflow`.

## Related Code Files

- Modify: `tests/unit/handlers/command_handlers/test_upload_meal_image_immediately_command_handler.py`
- Modify: `tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py`
- Modify: `tests/unit/handlers/command_handlers/test_food_guard_command_handlers.py`
- Modify: `tests/unit/api/test_app_smoke_routes.py`
- Create: `tests/unit/architecture/test_meal_analyze_graph_boundaries.py`
- Read only: `src/domain/model/meal/meal.py`
- Read only: `src/api/schemas/response/meal_responses.py`

## Tests Before

1. Add/verify direct upload READY meal regression with:
   - status READY
   - `source="scanner"`
   - calories derived from macros
   - image URL preserved
   - cache invalidation awaited
2. Add/verify scan-by-url READY meal regression with same scanner semantics.
3. Add/verify food-label scan regression with:
   - `source="food_label"`
   - `food_label_metadata` present
   - label parser path used
4. Add/verify no-food rejection does not save a Meal.
5. Add architecture test placeholders:
   - domain layer does not import `langgraph`
   - graph modules do not import vendor SDKs or `sentry_sdk` once created.

## Refactor

No refactor in this phase. Only add regression coverage and static guardrails.

## Tests After

No new behavior tests beyond the baseline checks.

## Implementation Steps

1. Read current handler tests and identify duplicate setup helpers.
2. Add missing direct upload baseline coverage.
3. Add missing scan-by-url baseline coverage.
4. Add missing food-label metadata baseline coverage.
5. Add architecture guardrail file with initial assertions that pass before graph modules exist.
6. Run focused tests.

## Todo List

- [x] Direct upload READY regression exists.
- [x] Scan-by-url READY regression exists.
- [x] Food-label READY regression exists.
- [x] No-food no-persistence regression exists.
- [x] Architecture guardrails added.
- [x] Focused tests pass.

## Success Criteria

- [x] Existing behavior is locked before refactor.
- [x] No production files changed except test-only architecture imports if needed.
- [x] Focused tests pass:

```bash
uv run pytest tests/unit/handlers/command_handlers/test_upload_meal_image_immediately_command_handler.py -q
uv run pytest tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py -q
uv run pytest tests/unit/handlers/command_handlers/test_food_guard_command_handlers.py -q
uv run pytest tests/unit/architecture/test_meal_analyze_graph_boundaries.py -q
```

## Risk Assessment

- Risk: tests depend on implementation details too tightly.
  Mitigation: assert domain/API-visible behavior and critical side effects, not private helper names.
- Risk: baseline tests duplicate existing fixtures.
  Mitigation: reuse current fake UoW and mock vision helpers where possible.

## Security Considerations

- Test fixtures must not include real image URLs with user data.
- No dotenv or provider credentials in fixtures.

## Regression Gate

```bash
uv run pytest tests/unit/handlers/command_handlers/test_upload_meal_image_immediately_command_handler.py tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py tests/unit/handlers/command_handlers/test_food_guard_command_handlers.py tests/unit/architecture/test_meal_analyze_graph_boundaries.py -q
```

## Next Steps

Proceed to Phase 2 only after baseline tests pass.

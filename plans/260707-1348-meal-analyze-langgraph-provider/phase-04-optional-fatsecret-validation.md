---
phase: 4
title: "Optional FatSecret Validation"
status: completed
priority: P1
effort: "1d"
dependencies: [3]
---

# Phase 4: Optional FatSecret Validation

## Context Links

- FatSecret adapter: `src/infra/adapters/fat_secret_service.py`
- Food reference repository: `src/infra/repositories/food_reference_repository_async.py`
- Food reference model: `src/infra/database/models/food_reference_model.py`
- Parse-text FatSecret divergence logic: `src/app/handlers/command_handlers/parse_meal_text_handler.py`
- Food mapping service: `src/domain/services/food_mapping_service.py`

## Overview

Add default-off FatSecret reference validation after vision parsing for plated
meal scans. This improves nutrition confidence without making FatSecret a hard
dependency and without new DB tables.

## Key Insights

- Current `search_foods()` enriches every search result with `food.get.v5`.
- Image analysis needs staged lookup: search first, score candidates, fetch details only for selected candidate(s).
- FatSecret validates reference nutrition; it does not identify image contents.
- `food_reference` is the first reusable source of truth.

## Requirements

- Functional: local verified `food_reference` match wins before FatSecret.
- Functional: FatSecret is called only when validation flag is enabled.
- Functional: FatSecret timeout/failure does not fail a valid scan.
- Functional: staged lookup does not call `food.get.v5` for every search hit.
- Functional: wrong/high-divergence FatSecret result is rejected.
- Non-functional: no raw provider payloads logged or persisted.
- Non-functional: no schema migration in this phase.

## Architecture

```text
parsed vision food item
  -> local normalized-name lookup
  -> if low confidence and flag enabled: FatSecret search-only
  -> score candidates
  -> fetch details for chosen candidate(s)
  -> compare provider macros vs AI estimate
  -> keep AI estimate or replace/reference-adjust item
```

Recommended provider seam:

```text
src/domain/ports/nutrition_reference_provider_port.py
src/app/services/food_reference_validation_service.py
src/infra/adapters/fatsecret_nutrition_reference_provider.py
```

Keep the interface small. Avoid generic multi-provider framework beyond current
FatSecret need.

## Related Code Files

- Create: `src/domain/ports/nutrition_reference_provider_port.py`
- Create: `src/app/services/food_reference_validation_service.py`
- Create: `src/infra/adapters/fatsecret_nutrition_reference_provider.py`
- Modify: `src/infra/adapters/fat_secret_service.py`
- Modify: `src/app/services/meal_analyze_workflow.py`
- Modify: `src/api/dependencies/event_bus.py`
- Modify: `src/infra/config/settings.py` if Phase 2 did not add all fields
- Create: `tests/unit/app/services/test_food_reference_validation_service.py`
- Modify: `tests/unit/infra/adapters/test_fat_secret_service.py`
- Create: `tests/unit/infra/adapters/test_fatsecret_nutrition_reference_provider.py`

## Tests Before

1. Add failing test for search-only FatSecret method:
   - returns candidates
   - does not call detail endpoint.
2. Add failing test for detail fetch only selected candidate.
3. Add failing test for local `food_reference` hit avoiding FatSecret.
4. Add failing test for FatSecret timeout returning original AI estimate.
5. Add failing test for divergence rejection.
6. Add failing test for flag disabled never calling FatSecret.

## Refactor

1. Add staged FatSecret methods:
   - `search_food_candidates(...)`
   - `get_food_details(...)`
2. Keep current `search_foods()` behavior for existing consumers.
3. Add a small nutrition reference provider adapter around FatSecret.
4. Add validation service that takes parsed food items and returns enriched items or warnings.
5. Integrate service into graph workflow only when flag is enabled and scan mode is plated meal.

## Tests After

1. Add graph execution test with one local match and one FatSecret match.
2. Add graph execution test where FatSecret fails and meal still persists READY.
3. Add privacy/logging test if new logs are introduced.

## Implementation Steps

1. Define provider candidate/detail DTOs or TypedDicts.
2. Add staged methods to FatSecret service without changing existing `search_foods()` contract.
3. Implement FatSecret nutrition reference adapter.
4. Implement validation service with local-first lookup and conservative scoring.
5. Integrate optional validation into workflow.
6. Ensure any source markers fit existing `FoodItem`/response shape without API-breaking additions.
7. Run focused tests.

## Todo List

- [x] Staged FatSecret methods added.
- [x] Nutrition reference provider port added.
- [x] FatSecret provider adapter added.
- [x] Validation service local-first behavior added.
- [x] Workflow optional validation wired behind flag.
- [x] Timeout and divergence tests pass.
- [x] Existing FatSecret consumers still pass.

## Success Criteria

- [x] FatSecret validation is default-off.
- [x] Valid scans do not depend on FatSecret availability.
- [x] No new DB tables.
- [x] Existing barcode/text FatSecret behavior remains compatible.
- [x] Tests pass:

```bash
uv run pytest tests/unit/infra/adapters/test_fat_secret_service.py tests/unit/infra/adapters/test_fatsecret_nutrition_reference_provider.py tests/unit/app/services/test_food_reference_validation_service.py -q
uv run pytest tests/unit/app/services/test_meal_analyze_workflow.py tests/unit/app/graphs/test_meal_analyze_graph_execution.py -q
```

## Risk Assessment

- Risk: FatSecret generic match worsens nutrition.
  Mitigation: require confidence threshold and divergence checks; fallback to AI estimate.
- Risk: provider adds latency.
  Mitigation: short timeout and max selected candidates.
- Risk: existing `search_foods()` tests break.
  Mitigation: add new staged methods instead of changing existing public method semantics.

## Security Considerations

- Do not log full FatSecret payloads, provider IDs tied to user context, or food payloads.
- Keep credentials in settings/env only.

## Regression Gate

```bash
uv run python -m compileall src/domain/ports src/app/services src/infra/adapters
uv run pytest tests/unit/infra/adapters/test_fat_secret_service.py tests/unit/app/services/test_food_reference_validation_service.py tests/unit/app/services/test_meal_analyze_workflow.py -q
```

## Next Steps

Proceed to Phase 5 after optional validation is safe under provider failure.

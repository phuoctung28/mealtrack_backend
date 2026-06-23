---
phase: 4
title: "Route and Legacy Coverage"
status: completed
priority: P2
effort: "3h"
dependencies: [3]
---

# Phase 4: Route and Legacy Coverage

## Context Links

- `src/api/routes/v1/meals.py`
- `src/api/routes/v1/meal_scan_by_url.py`
- `src/api/dependencies/event_bus.py`
- `tests/unit/api/test_app_smoke_routes.py`
- `tests/unit/api/test_small_v1_routers.py`
- `tests/integration/api/test_meals_api.py`
- `plans/260612-1046-service-initiated-bandwidth-reduction/phase-03-dead-code-removal.md`

## Overview

Protect the public API contract: explicit non-food still returns `NOT_FOOD_IMAGE`, provider outages still return outage semantics, and stale tests/routes do not hide a registered handler gap.

## Key Insights

- `/v1/meals/image/analyze` maps `RuntimeError`/`ValueError` from the command to `NOT_FOOD_IMAGE`.
- `/v1/meals/scan-by-url` maps the same error family to `NOT_FOOD_IMAGE`.
- Old tests mention `/v1/meals/image/analyze-url`, but current routes do not expose it. This mismatch must be documented or cleaned up during implementation.

## Requirements

- Functional: non-food upload and scan-by-url map to the existing `NOT_FOOD_IMAGE` error code.
- Functional: provider outage should not be misclassified as non-food if existing AI unavailable mapping is present.
- Functional: stale analyze-url test expectations are updated or removed only if proven dead.
- Non-functional: public success response shape unchanged.

## Architecture

Routes remain thin. No guard logic moves into API routes. Routes only translate expected handler errors into existing API exception shapes.

## Related Code Files

- Modify if needed: `src/api/routes/v1/meals.py`
- Modify if needed: `src/api/routes/v1/meal_scan_by_url.py`
- Modify: relevant API route tests under `tests/unit/api/` and `tests/integration/api/`
- Modify if needed: `src/api/dependencies/event_bus.py` only if legacy command is removed by coordinated dead-code cleanup.

## Implementation Steps

1. Add route-level tests for `ValueError("Image does not appear to contain food")` on upload and scan-by-url.
2. Confirm route response:
   - status matches current validation behavior.
   - `error_code == "NOT_FOOD_IMAGE"`.
   - message remains user-friendly.
3. Run/inspect provider outage tests to ensure `AIUnavailableError` is not converted into food validation.
4. Search current routes for `analyze-url`.
5. If no route exists, update stale tests/docs to avoid implying public support.
6. If `AnalyzeMealImageByUrlCommand` remains registered, keep Phase 3 guard. Do not remove it unless executing the dead-code phase from the bandwidth plan.

## Todo List

- [x] Upload API non-food mapping test.
- [x] Scan-by-url API non-food mapping test.
- [x] Provider outage classification preserved.
- [x] Analyze-url route/test mismatch resolved or documented.
- [x] No successful response-shape change.

## Success Criteria

- [x] API tests prove explicit non-food maps to `NOT_FOOD_IMAGE`.
- [x] Existing AI unavailable tests still pass.
- [x] No route-level food parsing introduced.
- [x] Legacy analyze-url surface is not misleading in tests/docs.

## Risk Assessment

- Risk: route catches broad `RuntimeError` as non-food today. Mitigation: do not broaden; focused tests preserve current outage handling where it exists.
- Risk: deleting legacy command during this plan causes wider blast radius. Mitigation: prefer guard now, deletion only in bandwidth dead-code plan.
- Risk: mobile depends on existing message. Mitigation: keep API error code stable; message can remain current.

## Security Considerations

- Error details must not include raw AI response, raw image URL, or user food payload.
- Keep existing auth dependency unchanged.

## Next Steps

Run focused verification and update project docs if needed.

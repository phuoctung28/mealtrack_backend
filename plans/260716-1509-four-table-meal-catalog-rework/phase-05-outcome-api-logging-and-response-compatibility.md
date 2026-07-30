---
phase: 5
title: "Outcome API Logging And Response Compatibility"
status: in_progress
priority: P1
effort: "2-3d"
dependencies: [4]
mode: tdd
---

# Phase 5: Outcome API Logging And Response Compatibility

## Overview

Expose renderable catalog meals and durable shown/selected/swapped/skipped/logged outcomes without breaking existing recommendation clients.

## Requirements

- Keep create/read/swap/log route paths and request aliases.
- Add owner-scoped idempotent `POST /{plan_id}/slots/{slot_id}/skip`.
- Include catalog name, description, image, instructions, derived calories, macros, and ingredient details in candidate responses.
- Log through normal `Meal`/`Nutrition`/`FoodItem` persistence with `food_reference_id` snapshots.
- Analytics reads bounded coarse outcomes; no raw event table.

## File Inventory

| Action | Files |
|---|---|
| Modify | `src/api/routes/v1/meal_recommendations.py`, `meal_recommendation_route_support.py` |
| Modify | `src/api/schemas/response/meal_recommendation_responses.py` |
| Create/modify | skip command and handler under `src/app/commands/meal_recommendation/` and `src/app/handlers/command_handlers/meal_recommendation/` |
| Create/modify | `MarkMealRecommendationShownCommand` and handler plus package exports |
| Modify | `src/app/services/recommended_meal_materialization_service.py`, `meal_recommendation_analytics_service.py`, `meal_recommendation_history_projector.py` |
| Modify | `src/api/dependencies/event_bus.py` for skip registration only |
| Verify unchanged | all `meal_suggestions` route/schema/handler/repository files |

## Tests Before

1. Characterize public route aliases, error mapping, feature gate, timezone/target snapshots, and response fields.
2. Lock normal materialization macro calculation and ingredient identity.
3. Add skip replay, owner, terminal-state, and conflict tests before handler code.

## Refactor

1. Replace recipe-version lookup with direct catalog lookup in materialization.
2. Map candidate rows into the retained plan/slot route shape, use `catalog_meal_id` fields, and add renderable catalog payloads. Remove release/version fields only after Phase 1 proves the contract is unshipped.
3. Dispatch an idempotent owner-scoped `MarkMealRecommendationShownCommand` after projection and before returning create/GET. Repository marks all returned candidates once; concurrent calls use `shown_at IS NULL` updates. Failure follows normal command error handling.
4. Implement state rules: shown is non-terminal; swap allowed only before skip/log; skip and log are terminal and mutually exclusive; operation rows replay identical historical requests; reused IDs with different payloads, skip->swap/log, and log->swap/skip return `409`.
5. Emit privacy-safe aggregate analytics from outcomes; remove release/event assumptions.
6. Keep `/v1/meal-suggestions` code untouched; run its full focused suite.

## Tests After And Regression Gate

`.venv/bin/python3.13 -m pytest -q tests/unit/api/test_meal_recommendations_route.py tests/unit/app/services/test_recommended_meal_materialization_service.py tests/unit/app/services/test_meal_recommendation_rollout_services.py tests/unit/app/services/test_meal_recommendation_history_projector.py tests/unit/api/test_meal_suggestions_routes.py tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py`

## Success Criteria

- [ ] Client can render every candidate without another catalog endpoint.
- [ ] Shown, selected/swapped, skipped, and logged outcomes are queryable.
- [ ] Logged meals preserve canonical ingredient IDs and derived calories.
- [ ] Existing AI suggestions remain behaviorally unchanged.

## Risks And Security

Responses must not expose internal user IDs, fingerprints, or operational metadata. Skip/log/swap require authenticated owner scope and rate limits.

## Next Steps

Run whole-feature verification, performance checks, docs sync, and controlled rollout.

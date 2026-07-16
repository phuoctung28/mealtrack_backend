---
phase: 5
title: "Durable Plans CQRS And API"
status: pending
priority: P1
effort: "7-10d"
dependencies: [4]
---

# Phase 5: Durable Plans CQRS And API

## Overview

Persist complete recommendation plans and expose owner-scoped create/read APIs through CQRS.

## Context Links

- [Plan](./plan.md)
- Existing composition: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/dependencies/event_bus.py`

## Key Insights

- Old `meal_plans` schema was deliberately dropped; use catalog-specific tables and models.
- UoW commits on context exit; repositories flush only.

## Requirements

- Functional: idempotent create, active/superseded lifecycle, durable 9 slots + 45 alternatives, recipe-version references, owner-scoped read.
- Non-functional: one transaction, no Redis/external calls, explicit response mapper, `allergy_evaluated=false`; allergies do not filter or block MVP results.

## Architecture

Tables: `meal_recommendation_plans`, `meal_recommendation_slots`, `meal_recommendation_slot_alternatives`. Snapshot timezone, target, algorithm/catalog version, score components, and plan/slot versions. Regeneration supersedes prior active plan but retains history.

## Related Code Files

- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/migrations/versions/<timestamp>_add_meal_recommendation_plan_tables.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/model/meal_recommendation/meal_recommendation_plan.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/ports/meal_recommendation_plan_repository_port.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/commands/meal_recommendation/create_three_day_meal_recommendation_command.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/queries/meal_recommendation/get_meal_recommendation_plan_query.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/services/meal_recommendation_target_resolver.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/ports/meal_recommendation_history_repository_port.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/meal_recommendations.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/schemas/response/meal_recommendation_responses.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/dependencies/event_bus.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/main.py`

## Implementation Steps

1. Add migration constraints/indexes for one slot per date/type, active lifecycle, recipe-version FKs, and idempotency uniqueness `(authenticated_user_id, operation, key)` with bounded key length and canonical request fingerprint.
2. Implement aggregate/mappers/repository with owner-scoped read and atomic save.
3. Reject client target overrides and start dates outside user-local today through +7 days. Resolve current backend target using `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/tdee_service.py`, custom macros, and `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/weekly_budget_service.py`; snapshot it across all three dates.
4. Add the dedicated 90-day linked-ingredient projection; handler resolves timezone, history/candidates, calls Phase 4, and persists the aggregate.
5. Register command/query handlers and mount `POST /v1/meal-recommendations/three-day` plus `GET /v1/meal-recommendations/{id}`.
6. Claim idempotency in a savepoint/short transaction; on unique violation re-read by owner/operation/key, authorize first, verify fingerprint, replay identical request, and conflict on mismatch.
7. Apply authenticated user/IP-fallback generation limits and serialize active generation per owner. Retain superseded plans in MVP; revisit archival/retention after measured volume.
8. Test cross-user/cross-operation same keys, concurrent identical keys, >500-meal history, not-found, insufficiency, regeneration, rollback, response totals, and zero runtime provider calls.

## Todo

- [ ] Migration and aggregate constraints pass.
- [ ] Create/read wiring is production-registered.
- [ ] Idempotency and ownership tests pass.

## Success Criteria

- [ ] Exactly one complete aggregate persists per successful request.
- [ ] API p95 target <500 ms is measured with representative seeded data.

## Risk Assessment

Partial aggregate writes or duplicate active plans. Mitigation: DB constraints, request fingerprint, and single UoW transaction.

## Security Considerations

All repository predicates include authenticated user ID; cross-user access returns indistinguishable 404; target override is disabled; allergy state does not imply safety evaluation.

## Next Steps

- Phase 6 adds mutation and logging against persisted slots.

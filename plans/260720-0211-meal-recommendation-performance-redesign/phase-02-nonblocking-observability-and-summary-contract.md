---
phase: 2
title: "Nonblocking Observability And Summary Contract"
status: completed
priority: P1
effort: "2d"
dependencies: [1]
mode: tdd
---

# Phase 2: Nonblocking Observability And Summary Contract

## Overview

Remove PostHog network waits from HTTP latency and replace the unreleased full-plan response with one compact plan contract plus owner-scoped lazy slot detail.

## Requirements

- Create and get return plan metadata and nine selected slot summaries: IDs, date/type, meal identity/name/cuisine/image, backend-derived calories/macros, selection version, and logged meal ID.
- Summary omits description, ingredients, scores, and alternatives.
- `GET /v1/meal-recommendations/{plan_id}/slots/{slot_id}` returns one fully hydrated selected meal and that slot's alternatives.
- Create and idempotent replay must not hydrate the 54-candidate graph.
- Analytics runs through `BackgroundTaskManager`; failures never change endpoint status.
- Stage metrics cover target, idempotency, snapshot, affinity, ranking, persistence, hydration, serialization, and analytics enqueue.

## File Inventory

| Action | Files |
|---|---|
| Modify | `src/api/routes/v1/meal_recommendations.py`, `meal_recommendation_route_support.py` |
| Modify | `src/api/schemas/response/meal_recommendation_responses.py` |
| Modify | meal recommendation query/handler exports and `meal_recommendation_plan_repository_port.py` |
| Modify | `src/infra/repositories/meal_recommendation_plan_repository_async.py` |
| Modify | `src/api/base_dependencies.py`, task-manager and API lifecycle composition |
| Modify | `src/app/services/meal_recommendation_analytics_service.py`, `src/infra/adapters/posthog_adapter.py` |
| Extend | route, HTTP-contract, analytics-service, and background-task-manager tests |
| Add if client reuse is implemented | `tests/unit/infra/adapters/test_posthog_adapter.py` |

## Function And Interface Checklist

- Add repository `get_summary(...)` and `get_slot_detail(...)`; never call `_rows_to_plan()` for them.
- Add lightweight creation replay metadata/projection so replay returns the compact plan directly.
- Replace `to_response(...)` with compact-plan and slot-detail serializers.
- Snapshot a bounded privacy-safe analytics payload and schedule one background task.
- Reuse one lifecycle-managed PostHog client and close it at shutdown.

## Tests Before

1. Create/get expose one compact response contract in HTTP and OpenAPI.
2. Compact response contains nine slots, no ingredients/alternatives, and is <35% of the phase-1 payload.
3. Slot detail is owner-scoped/404-safe and hydrates only one slot.
4. Create/replay performs no full-plan hydration.
5. A blocked analytics adapter cannot block HTTP completion; background failure cannot change success.
6. Metric tests inject a clock and assert low-cardinality labels/counts, not milliseconds.

## Refactor

1. Replace the unreleased full-plan DTO with compact plan and slot-detail DTOs.
2. Add compact repository/query projections with owner-anchor authorization.
3. Schedule analytics using the process-wide task manager, never raw `asyncio.create_task`.
4. Batch route events into one task and add stage metrics without IDs.

## Tests After And Regression Gate

```bash
.venv/bin/python3 -m pytest -q tests/unit/api/test_meal_recommendations_route.py tests/unit/api/test_meal_recommendation_http_contract.py tests/unit/app/services/test_meal_recommendation_analytics_service.py tests/unit/infra/event_bus/test_background_task_manager.py
```

## Success Criteria

- [x] Create/get expose only the compact plan contract.
- [x] Summary/detail query only required rows and enforce owner scope.
- [x] PostHog latency/failure is outside the HTTP critical path.
- [x] Stage metrics explain create/read time without high-cardinality labels.

## Completion Evidence

- Added compact plan and slot-detail response models.
- Added owner-scoped summary/detail repository projections and query handler wiring.
- Routed recommendation analytics through `BackgroundTaskManager` when available.
- Verified with focused API, handler, repository, analytics, and HTTP-contract tests.

## Risks And Security

Do not place domain objects or sessions in background tasks. Snapshot only sanitized scalar analytics fields before the UoW closes.

## Next Steps

Wire the compact contract into Flutter after target-slot mutation support is complete.

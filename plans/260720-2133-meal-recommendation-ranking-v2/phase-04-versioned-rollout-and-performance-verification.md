---
phase: 4
title: "Direct V2 Wiring And Performance Verification"
status: in-progress
priority: P1
effort: "1-2d plus staging verification"
dependsOn: [1, 2, 3]
---

# Phase 4: Direct V2 Wiring And Performance Verification

## Context Links

- [Plan overview](./plan.md)
- [Bounded diversity phase](./phase-03-bounded-diversity-and-alternative-ranking.md)
- [Create handler](../../src/app/handlers/command_handlers/meal_recommendation/create_three_day_meal_recommendation_command_handler.py)
- [Event-bus composition](../../src/api/dependencies/event_bus.py)
- [Analytics service](../../src/app/services/meal_recommendation_analytics_service.py)

## Overview

- **Priority:** P1.
- **Status:** In progress.
- **Goal:** wire the new deterministic ranking directly for new plan generation, keep persisted replay deterministic, and verify local/staging performance before merge/deploy.
- **Release rule:** no runtime feature flag or staged rollout mode is needed because this branch has not shipped to production.

## Requirements

- Compose `ThreeDayPlanOptimizer()` at the event-bus boundary for new create requests.
- Keep idempotency lookup before catalog access, history access, or optimizer work.
- Existing persisted plans replay their stored candidates and scores without recalculation.
- Keep swap/log mutation results and analytics free of algorithm-version metadata.
- Warm create p95 remains `<500 ms`; compact read and changed-slot mutations remain `<300 ms`; cold refresh plus create remains `<1,000 ms` on staging.
- Full unit suite, import boundaries, Ruff, compile checks, and synthetic benchmark must pass before merge/deploy.

## Architecture And Data Flow

```text
create handler
  -> owner lock + idempotent replay (stored version wins)
  -> snapshot + aggregate affinity + snapshot ingredient statistics
  -> ThreeDayPlanOptimizer()
  -> existing repository and response mapper

swap/log -> existing changed-slot response
         -> existing analytics capture
         -> unchanged slot-detail HTTP payload
```

## Related Code Files

### Modify

- `src/api/dependencies/event_bus.py`
- `src/app/handlers/command_handlers/meal_recommendation/create_three_day_meal_recommendation_command_handler.py`
- `src/domain/model/meal_recommendation/meal_recommendation_plan.py` to remove algorithm-version metadata.
- `src/infra/repositories/meal_recommendation_plan_repository_async.py` to remove algorithm-version persistence.
- `src/app/services/meal_recommendation_analytics_service.py`
- `src/api/routes/v1/meal_recommendation_route_support.py`
- `src/api/routes/v1/meal_recommendations.py` to keep analytics calls on the simplified contract.
- `scripts/testing/benchmark_meal_recommendation_performance.py`
- Endpoint, handler, analytics, repository, and event-bus tests.
- `docs/api-endpoints.md`, `docs/system-architecture.md`, and `docs/project-roadmap.md`.

### Delete

- Runtime rollout settings and version-router test artifacts from the earlier unshipped plan shape.

## Todo List

- [x] Event-bus composition uses the new ranking directly for new plan generation.
- [x] Replay bypasses recalculation and version selection.
- [x] Swap/log analytics keep the simplified contract without algorithm-version metadata.
- [x] Focused and full unit gates pass before the rollout simplification.
- [x] Local synthetic benchmark passes and is labeled correctly.
- [x] Focused and full unit gates pass after removing rollout settings.
- [ ] Staging p95 and quality evidence is recorded before merge/deploy.

## Tests After

```bash
.venv/bin/python -m pytest -q \
  tests/unit/domain/services/meal_recommendation \
  tests/unit/app/services/test_catalog_meal_snapshot_service.py \
  tests/unit/app/services/test_meal_recommendation_history_projector.py \
  tests/unit/app/services/test_meal_recommendation_analytics_service.py \
  tests/unit/app/handlers/test_meal_recommendation_handlers.py \
  tests/unit/api/test_event_bus_dependency_singletons.py \
  tests/unit/api/test_meal_recommendation_http_contract.py \
  tests/unit/api/test_meal_recommendations_route.py \
  tests/unit/infra/repositories/test_meal_recommendation_plan_repository_async.py
.venv/bin/python -m pytest -q tests/unit
.venv/bin/python -m compileall -q \
  src/domain/services/meal_recommendation \
  src/app/services \
  src/app/handlers/command_handlers/meal_recommendation
.venv/bin/ruff check src tests scripts/testing/benchmark_meal_recommendation_performance.py
.venv/bin/lint-imports
git diff --check
```

## Regression Gate

- All v1 and v2 domain goldens pass.
- Existing five route paths and compact/detail/delta response field sets are unchanged.
- Persisted v1 and v2 plans replay without catalog/history/optimizer work.
- No migration, new table/index, full-plan hydration, warm catalog SQL, or mobile change.
- Local benchmark is supportive evidence only; merge/deploy remains gated by staging p95 and representative quality checks.

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Old plans change after v2 wiring | Idempotent replay before selection and stored algorithm/candidate scores. |
| V2 changes endpoint contracts | Contract tests cover compact/detail/delta response field sets. |
| V2 adds too much warm latency | Snapshot-scoped statistics and bounded top-30 reranking; verify local and staging p95. |
| Analytics leaks catalog detail | Existing allowlisted properties only add stored algorithm version. |

## Security Considerations

- Owner scope, authentication, idempotency, and operation replay stay unchanged.
- Analytics properties are allowlisted and tested against meal, ingredient, history, email, and token fields.
- No new secret, environment variable, database table, or external service is required.

## Next Steps

Finish post-simplification tests locally, then capture staging p95 and representative quality evidence before merge/deploy.

## Unresolved Questions

- None.

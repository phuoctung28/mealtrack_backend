---
phase: 7
title: "Performance Rollout And Documentation"
status: completed-local
priority: P1
effort: "1-2d"
dependencies: [3, 4, 5, 6]
mode: tdd
---

# Phase 7: Performance Rollout And Documentation

## Overview

Prove deterministic, database, concurrency, latency, payload, and mobile-startup gains; deploy in reversible order; document operations.

## Requirements

- Unit CI gates golden parity, call/query counts, SQL shape, payload ratio, cache state, and the final HTTP contract.
- Only a pinned runner or staging gates absolute p95.
- Benchmark 180/1,000/5,000 catalogs with fixed inputs, 10 warmups, >=50 samples, and runner metadata.
- Record SQL count, hydrated rows, response bytes, snapshot refreshes, stage histograms, p50, and p95.
- Backend and mobile ship one final contract; the recommendation feature stays disabled if either side fails integration.

## File Inventory

| Action | Files |
|---|---|
| Finalize | `scripts/testing/benchmark_meal_recommendation_performance.py` |
| Conditional | CI/staging load job only if a pinned runner exists |
| Update | `docs/api-endpoints.md`, `docs/system-architecture.md`, `docs/database-guide.md`, `docs/troubleshooting.md` |
| Update | roadmap/changelog when implementation status changes |
| Evidence | `plans/reports/meal-recommendation-performance-final.json` and query plans |

## Verification Matrix

| Gate | Target |
|---|---|
| Active compact-plan read | p95 <300 ms |
| Swap/log changed-slot response | p95 <300 ms |
| Warm create | p95 <500 ms; zero full-catalog SQL |
| Cold snapshot refresh + create | p95 <1,000 ms |
| 5,000 vs 1,000 optimizer | no superlinear pass growth; pinned p95 <=3x |
| Compact payload | <35% of phase-1 fixture |
| Slot mutation | no full-plan hydration; lock <=6 candidate rows |
| Mobile first state | cached plan visible before remote completion |

## Tests Before

1. Completed focused backend and Flutter suites from phases 1-6.
2. Completed local owner/replay/idempotency regression coverage; real PostgreSQL concurrency remains a staging gate.
3. Captured before/after JSON locally with matching script metadata.
4. Verified `/v1/meal-suggestions` regressions remain unchanged and green.

## Rollout

1. Complete backend and Flutter contract integration before enabling the unreleased feature.
2. Warm one snapshot per process and observe refresh/error metrics; startup must not depend on Neon.
3. Canary the complete feature internally, then enable the compact-plan/changed-slot flow.
4. Monitor latency/error, snapshot age/failure, affinity query rows/time, replay conflicts, and mobile refresh failure.
5. If contract errors rise, disable the unreleased recommendation feature and revert the paired backend/mobile change.

## Tests After And Regression Gate

```bash
.venv/bin/python3 -m pytest -q tests/unit/domain/services/meal_recommendation tests/unit/app/services/test_meal_recommendation_history_projector.py tests/unit/app/services/test_meal_recommendation_analytics_service.py tests/unit/app/handlers/test_meal_recommendation_handlers.py tests/unit/infra/repositories/test_catalog_recipe_repository_async.py tests/unit/infra/repositories/test_meal_recommendation_plan_repository_async.py tests/unit/api/test_meal_recommendations_route.py tests/unit/api/test_meal_recommendation_http_contract.py
.venv/bin/python3 scripts/testing/benchmark_meal_recommendation_performance.py --catalog-sizes 180,1000,5000 --output plans/reports/meal-recommendation-performance-final.json
/Users/alexnguyen/flutter/bin/flutter test test/features/meal_recommendation
```

## Success Criteria

- [x] Deterministic, HTTP-contract, owner, and idempotency regressions pass locally.
- [ ] Every performance gate is evidenced on its intended runner; staging p95 remains a rollout gate.
- [x] The unreleased feature can be disabled or reverted without data migration.
- [x] Active docs explain snapshot lifecycle, compact/delta contracts, metrics, and troubleshooting.
- [x] No Redis result cache, speculative index, or compatibility branch entered scope.

## Risks And Security

Use dedicated staging users and idempotency keys. Never load-test production accounts or expose IDs in metrics.

## Next Steps

Proceed to staging p95 and real-PostgreSQL concurrency verification before production rollout.

---
phase: 1
title: "Baseline And Contract Characterization"
status: completed
priority: P1
effort: "1-2d"
dependencies: []
mode: tdd
---

# Phase 1: Baseline And Contract Characterization

## Overview

Freeze current deterministic behavior, owner/idempotency guarantees, query/hydration cost, and reproducible performance evidence before changing architecture.

## Context Links

- [Approved brainstorm](../reports/brainstorm-260720-0205-recommendation-performance-redesign.md)
- `src/domain/services/meal_recommendation/three_day_plan_optimizer.py`
- `src/api/routes/v1/meal_recommendations.py`
- `src/infra/repositories/meal_recommendation_plan_repository_async.py`

## Requirements

- Characterize exact selected and alternative IDs for normal, affinity, tolerance-fallback, and reversed-input cases.
- Record response bytes, SQL count, rows hydrated, catalog refresh count, and stage timings without making noisy wall-clock values unit-test gates.
- Preserve owner scope, idempotency, operation replay, and recommendation semantics; the unreleased response shape is only a before/after measurement baseline.

## File Inventory

| Action | Files |
|---|---|
| Extend | `tests/unit/domain/services/meal_recommendation/test_deterministic_recommendation_domain.py` |
| Extend | `tests/unit/api/test_meal_recommendations_route.py` |
| Add | `tests/unit/api/test_meal_recommendation_http_contract.py` |
| Add | `scripts/testing/benchmark_meal_recommendation_performance.py` |
| Evidence | `plans/reports/meal-recommendation-performance-baseline.json` |

## Tests Before

1. Add golden fixtures with exact 9 selected and 45 alternative IDs, scores/rounding, sparse catalog, and shuffled input.
2. Add instrumented fake repositories/scorers for catalog, history, persistence, serialization, and analytics call counts.
3. Record current JSON/OpenAPI size and fields for before/after comparison while locking mutation replay behavior.
4. Add an explicit benchmark with fixed 180/1,000/5,000 catalogs, 10 warmups, at least 50 samples, `perf_counter_ns`, and runner metadata.
5. Use `asyncio.Event`, not sleeps, to characterize the current analytics wait.

## Refactor

No production behavior changes. Only test seams and repeatable evidence collection are allowed.

## Tests After And Regression Gate

```bash
.venv/bin/python3 -m pytest -q tests/unit/domain/services/meal_recommendation/test_deterministic_recommendation_domain.py tests/unit/api/test_meal_recommendations_route.py tests/unit/api/test_meal_recommendation_http_contract.py
.venv/bin/python3 scripts/testing/benchmark_meal_recommendation_performance.py --catalog-sizes 180,1000,5000 --output plans/reports/meal-recommendation-performance-baseline.json
```

## Success Criteria

- [x] Golden outputs cover selection, alternatives, fallback, affinity, and input-order stability.
- [x] Owner scope, idempotency replay, and recommendation semantics are locked.
- [x] Baseline reports response bytes, SQL count, hydrated rows, p50/p95, and runner metadata.
- [x] Unit CI uses deterministic counts and shapes, not fragile absolute timings.

## Completion Evidence

- Added deterministic optimizer goldens for normal and affinity-weighted plans.
- Added HTTP contract characterization for current full-plan payload, OpenAPI fields, and synchronous analytics wait.
- Added synthetic benchmark evidence at `plans/reports/meal-recommendation-performance-baseline.json`.
- Verified with the Phase 1 pytest gate, benchmark script, and focused ruff check.

## Risks And Security

Use synthetic fixtures only. Redact DSNs and tokens from benchmark evidence.

## Next Steps

Use these goldens as the non-negotiable regression gate for phases 2-5.

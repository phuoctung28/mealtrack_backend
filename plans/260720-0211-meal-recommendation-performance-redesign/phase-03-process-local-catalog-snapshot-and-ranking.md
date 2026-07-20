---
phase: 3
title: "Process-Local Catalog Snapshot And Ranking"
status: completed
priority: P1
effort: "2-3d"
dependencies: [1]
mode: tdd
---

# Phase 3: Process-Local Catalog Snapshot And Ranking

## Overview

Compile active catalog meals once per process/revision and replace repeated full-catalog ranking passes with deterministic ranked pools.

## Requirements

- Cache a frozen tuple of fully resolved `CatalogMeal`, revision, expiry, and refresh time in one process-scoped service.
- Default TTL 300 seconds; expiry runs a lightweight revision query before any hydration.
- One async lock plus double-check prevents refresh stampedes.
- Revision covers active catalog count/max `meal_catalog.updated_at` and max linked `food_reference.updated_at`; serving-size updates must advance the parent timestamp.
- Read revision before/after hydration and retry once if import changed concurrently.
- Cold failure returns typed catalog-unavailable; warm refresh failure serves last good data and retries after 30 seconds with a metric.
- No Redis recommendation-result cache.
- Rank once per meal type/target, then deterministically partition unique winners and five alternatives per slot.
- A newly persisted plan returns the already-built immutable projection after flush instead of reloading 54 rows and catalog relationship trees.

## File Inventory

| Action | Files |
|---|---|
| Add | `src/app/services/catalog_meal_snapshot_service.py` |
| Modify | `src/domain/ports/catalog_recipe_repository_port.py` |
| Modify | `src/infra/repositories/catalog_recipe_repository_async.py` |
| Modify | `src/infra/repositories/meal_recommendation_plan_repository_async.py` |
| Modify | create recommendation handler, `src/api/dependencies/event_bus.py`, settings |
| Modify | scoring, optimizer, and alternative-selection domain services |
| Add | `tests/unit/app/services/test_catalog_meal_snapshot_service.py` |
| Extend | catalog repository, event-bus singleton, deterministic optimizer tests |

## Function And Interface Checklist

- `CatalogMealRepositoryPort.get_active_catalog_revision()` returns an immutable comparable value.
- `CatalogMealSnapshotService.get_snapshot(uow)` exposes an immutable tuple and no mutation API.
- Event-bus composition injects one shared snapshot service into copied create handlers.
- Scoring builds immutable pools keyed by meal type/target.
- Keep `ALGORITHM_VERSION` only if every phase-1 golden remains exact.

## Tests Before

1. Cold hydrates once; warm executes zero catalog SQL.
2. Twenty concurrent cold callers produce one load; cancelled waiter does not poison refresh.
3. Unchanged revision reuses; changed revision refreshes; mid-load change retries once.
4. Cold failure fails closed; warm refresh failure serves last good and records age/retry metrics.
5. Returned snapshot is immutable.
6. Counting scorer proves one score per eligible meal/type-target.
7. Optimizer matches all phase-1 goldens for normal, affinity, fallback, and shuffled input.
8. Fresh persistence performs no `_load_batch()` after flush; conflict/replay behavior remains correct.

## Refactor

1. Add revision query without ORM relationship hydration.
2. Implement single-flight snapshot lifecycle with an injected monotonic clock.
3. Compose one service per API process.
4. Extract ranked pools and partition winners first, then alternatives excluding all winners.
5. Preserve formula, rounding, and `(-score, catalog_meal.id)` tie break.
6. Return the in-memory immutable compact plan after successful flush; keep compact projection reads for replay/conflict paths.

## Tests After And Regression Gate

```bash
.venv/bin/python3 -m pytest -q tests/unit/app/services/test_catalog_meal_snapshot_service.py tests/unit/infra/repositories/test_catalog_recipe_repository_async.py tests/unit/api/test_event_bus_dependency_singletons.py tests/unit/domain/services/meal_recommendation/test_deterministic_recommendation_domain.py
```

## Success Criteria

- [x] Warm generation performs no catalog hydration or nutrition conversion.
- [x] Fresh generation performs no post-save full-plan reload.
- [x] Concurrent refreshes hydrate once and never expose partial state.
- [x] 180/1,000/5,000 catalogs show linear scoring-call growth.
- [x] Output stays golden-identical or deliberately bumps algorithm version with evidence.

## Completion Evidence

- Added process-local catalog snapshot service with revision checks, TTL, lock, and last-good fallback.
- Added active catalog revision query.
- Injected one snapshot service into configured recommendation creation handlers.
- Changed fresh persistence to return the in-memory plan after flush.
- Reworked optimizer to partition selected slots and alternatives from ranked pools while preserving goldens.

## Risks And Security

Never key the snapshot by user. Importer and canonical nutrition tests must prove revision timestamps advance.

## Next Steps

Combine the warm snapshot with aggregate affinity.

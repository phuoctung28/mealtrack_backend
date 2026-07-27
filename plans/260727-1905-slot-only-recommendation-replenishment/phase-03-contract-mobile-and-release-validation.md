---
phase: 3
title: "Contract, Mobile, And Release Validation"
status: pending
priority: P1
effort: "1-1.5d"
dependencies: [2]
---

# Phase 3: Contract, Mobile, And Release Validation

## Overview

Prove backend compatibility, explicitly record that Flutter needs no source change under the retained contract, and release behind measured database-pool safeguards.

## Related Code Files

- Modify: `docs/meal-recommendation-mobile-handoff.md`
- Modify: `docs/system-architecture.md`
- Modify: `docs/project-changelog.md` if present
- Verify only: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/core/network/api_service.dart`
- Verify only: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/meal_recommendation/data/repositories/meal_recommendation_repository_impl.dart`
- Verify only: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/test/features/meal_recommendation/application/providers/meal_recommendation_controller_test.dart`

## Requirements

- No mobile codegen, schema, mapper, repository, or UI change if the endpoint body and response shape remain unchanged.
- Add Flutter tests only if the backend needs a new visible state or changes its error/response contract.
- Document that daily readiness and cron remain deferred.
- Verify on staging with actual database pool metrics before production enablement.

## Implementation Steps

1. Run backend unit, architecture, migration, and PostgreSQL concurrency tests; isolate and report pre-existing failures separately.
2. Run focused Flutter recommendation tests against existing slot-patch expectations; do not add e2e work.
3. Inspect generated OpenAPI diff and Flutter API models to prove compatibility.
4. Stage a repeated-swap scenario while observing `/v1/health/db-pool`, request latency, and SQL query count; do not label a local run as production proof.
5. Update handoff/architecture/changelog docs with the slot-only invariant, lifecycle semantics, metrics, rollback, and deferred daily job.

## Success Criteria

- [ ] Backend API stays backward compatible.
- [ ] Flutter source changes: none, unless contract proof disproves this assumption.
- [ ] Staging proves unrelated slots are unchanged and no pool checkout remains held after swaps.
- [ ] Rollback is a feature/code rollback; candidate history remains harmless and readable.

## Risk Assessment

The app currently has a small deployed pool in the reported incident. Staging must prove bounded transaction duration before rollout; pool-size tuning is a separate operational decision.

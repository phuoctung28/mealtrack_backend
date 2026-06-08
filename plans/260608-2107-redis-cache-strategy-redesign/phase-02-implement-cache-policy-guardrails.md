---
phase: 2
title: Implement cache policy guardrails
status: completed
priority: P1
effort: 3h
dependencies:
  - 1
---

# Phase 2: Implement cache policy guardrails

## Overview

Implement minimal code guardrails that make the cache policy real without introducing a database migration.

## Requirements

- Functional: nutrition lookup writes through the injected Redis wrapper; meal suggestion lookups avoid `KEYS`; unused hash helpers are removed if no active callers remain.
- Non-functional: no public API contract or schema change; keep Redis optional only for true cache paths and required for suggestion sessions until a future Postgres migration.

## Architecture

Use `RedisClient` as the wrapper abstraction for cache-style operations. Keep raw Redis access encapsulated inside infrastructure classes only when the wrapper intentionally exposes a property. Meal suggestion sessions remain Redis-backed transient state in this PR, with deterministic suggestion index keys to avoid keyspace scans.

## Related Code Files

- Modify: `src/infra/cache/redis_client.py`
- Modify: `src/infra/repositories/meal_suggestion_repository.py`
- Modify: `src/domain/services/meal_suggestion/nutrition_lookup_service.py`
- Modify: `src/api/base_dependencies.py`
- Modify/Delete: `tests/unit/infra/test_redis_hash_ops.py`
- Modify/Add: targeted meal suggestion and nutrition cache tests
- Modify: docs touched by cache policy wording

## Implementation Steps

1. Remove unused Redis hash helpers and stale tests after confirming no active callers.
2. Update `NutritionLookupService._cache_result` to use the same wrapper contract as reads.
3. Add/adjust nutrition cache tests so wrapper-style `set(..., ttl=...)` is verified.
4. Update meal suggestion repository naming/messages to state "session store", not generic cache.
5. Replace suggestion lookup by Redis `KEYS` with deterministic `suggestion_id -> session_id` index keys on save/update.
6. Keep a bounded `SCAN` fallback for legacy 4-hour keys if needed.
7. Align dependency error messages and docs with required transient state.

## Success Criteria

- [ ] No active production code uses Redis `KEYS`.
- [ ] No active production code calls removed hash helpers.
- [ ] Nutrition cache writes work against the injected `RedisClient` wrapper.
- [ ] Existing meal suggestion repository methods preserve behavior.
- [ ] Docs and config comments stay consistent with the new cache policy.

## Risk Assessment

Legacy suggestions saved before deploy may not have index keys. Keep a short-lived `SCAN` fallback to preserve behavior during the 4-hour TTL window.

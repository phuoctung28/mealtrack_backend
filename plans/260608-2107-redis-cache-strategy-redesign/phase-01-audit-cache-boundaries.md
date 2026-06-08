---
phase: 1
title: Audit cache boundaries
status: completed
priority: P1
effort: 1h
dependencies: []
---

# Phase 1: Audit cache boundaries

## Overview

Audit active Redis call sites and classify each as optional cache, required transient state, computed read model, or external cache pointer. This phase locks the implementation boundary before code edits.

## Requirements

- Functional: identify active callers of Redis hash helpers, raw Redis methods, and production-unsafe key scans.
- Non-functional: keep the audit grounded in `src/` and active tests, not stale generated docs.

## Architecture

The cache policy source of truth is `docs/superpowers/specs/2026-05-21-redis-optimize-design.md`. Active code should map to one of the documented categories.

## Related Code Files

- Read: `src/infra/cache/redis_client.py`
- Read: `src/infra/cache/cache_service.py`
- Read: `src/infra/repositories/meal_suggestion_repository.py`
- Read: `src/domain/services/meal_suggestion/nutrition_lookup_service.py`
- Read: `src/api/base_dependencies.py`
- Read: `tests/unit/infra/test_redis_hash_ops.py`
- Read: `tests/unit/domain/services/meal_suggestion/test_nutrition_redis_cache.py`

## Implementation Steps

1. Search active source/tests for `hset_batch`, `hgetall_batch`, raw `.client.keys`, and raw `.setex`.
2. Confirm notification precompute/dispatch does not use Redis hashes.
3. Confirm meal suggestion Redis behavior is required state, not optional cache.
4. Record exact code changes needed for Phase 2.

## Success Criteria

- [ ] Active Redis hash helper callers are known.
- [ ] Raw Redis contract mismatches are known.
- [ ] Meal suggestion lookup path can be fixed without API/schema changes.

## Risk Assessment

Hidden callers are the main risk. Use `rg` against `src/` and `tests/`; ignore historical docs except where updating documentation.

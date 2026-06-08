---
title: Redis cache strategy redesign
description: Implement selective Redis cache policy guardrails
status: completed
priority: P2
branch: codex/redis-cache-strategy-redesign
tags:
  - redis
  - cache
  - architecture
blockedBy: []
blocks: []
created: '2026-06-08T14:07:12.318Z'
createdBy: 'ck:plan'
source: skill
---

# Redis cache strategy redesign

## Overview

Redesign Redis usage around a selective cache policy instead of broad "cache everything" behavior. This plan turns the 2026-06-08 cache strategy into code guardrails: optional caches use `CachePort`/`CacheService`, Redis-backed meal suggestion sessions are named and treated as required transient state, dead notification-hash cache APIs are removed, and docs/config stop promising universal Redis fallback.

Expected output: code and documentation changes on branch `codex/redis-cache-strategy-redesign`, verified by focused unit tests plus lint/syntax checks, then pushed as a GitHub PR.

Acceptance criteria:
- Optional Redis cache paths still degrade by bypassing cache.
- Meal suggestion sessions no longer look like cache-aside in names, docs, dependency messages, or tests.
- Nutrition lookup cache uses one stable client abstraction and writes successfully through the injected wrapper.
- Redis `KEYS` and unused notification hash helper APIs are not retained in active production/cache code.
- Notification precompute/dispatch remains database-owned.
- No public API response shape or DB schema change in this PR.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Audit cache boundaries](./phase-01-audit-cache-boundaries.md) | Completed |
| 2 | [Implement cache policy guardrails](./phase-02-implement-cache-policy-guardrails.md) | Completed |
| 3 | [Verify and ship](./phase-03-verify-and-ship.md) | Completed |

## Dependencies

- No overlapping unfinished local plan found under `./plans/`.
- Depends on existing Redis strategy doc: `docs/superpowers/specs/2026-05-21-redis-optimize-design.md`.

## Scope Boundary

In scope:
- Code-level cache/state naming and abstraction cleanup.
- Nutrition lookup Redis wrapper compatibility.
- Meal suggestion Redis repository guardrails that avoid production-unsafe commands.
- Removal of unused Redis hash helpers and tests if no active callers exist.
- Documentation updates already started for the cache admission policy.

Out of scope:
- Moving meal suggestion sessions to Postgres.
- Adding a new migration or cleanup job.
- Reworking all query caches in one sweep.
- Reintroducing Redis into notification precompute or dispatch.

## Red-Team Notes

- Risk: removing Redis hash helpers could break hidden callers. Mitigation: `rg` all active `src/` and `tests/` before delete; keep only if a real caller remains.
- Risk: replacing `KEYS` lookup for suggestions could make update-by-suggestion-id impossible. Mitigation: preserve existing public repository methods by adding deterministic suggestion index keys at save time and fallback `SCAN` only for legacy keys.
- Risk: changing required-state behavior could break existing endpoints when Redis is absent. Mitigation: do not pretend to add fallback; preserve required Redis behavior but rename and fail with clearer message.

# Selective Cache Admission Policy

**Status:** Accepted
**Date:** 2026-06-08
**Scope:** Backend caching architecture for Redis, process-local caches, and computed read models.

## Context

MealTrack has several cache-like mechanisms:

- Redis-backed optional caches for food lookup, nutrition lookup, computed read models, and Gemini cache names.
- Process-local TTL cache for Firebase UID to active user ID mapping.
- Redis-backed meal suggestion sessions, which are transient product state rather than cache-aside.
- Database-owned notification rows, notification context, FCM token ownership, meals, metrics, and subscriptions.

The architectural risk is not "Redis is bad." The risk is using cache as the default answer for every repeated read. That creates stale-data bugs, hidden availability coupling, high Redis command volume, broad invalidation scans, and unclear source-of-truth ownership.

The current policy in `docs/superpowers/specs/2026-05-21-redis-optimize-design.md` already points in the right direction: default to no cache unless the value earns the added complexity. This ADR accepts that direction as the backend rule.

## Decision

Cache admission is strict. Do not cache by default.

A value can use Redis or another cache only when all are true:

1. A source of truth exists outside the cache.
2. The read is expensive or frequent enough to justify the extra operation.
3. A stale value is acceptable for a named TTL window.
4. The invalidation trigger is known and wired, or the TTL is short enough to bound risk.
5. Cache failure falls back to correct behavior.
6. Expected command volume fits the Redis budget at projected user count.
7. The key has a named owner and documented source of truth.

If any item fails, use the database, compute on demand, or model the data as required state. Do not pretend required state is cache-aside.

## Category Rules

| Category | Rule | Current Examples |
|---|---|---|
| Optional cache | Redis allowed. Miss/error must bypass cache and read source of truth. | Food search/details, nutrition lookup |
| Computed read model | Redis allowed only with short TTL and reliable write invalidation. | Daily macros, weekly budget, hydration, nutrition bulk |
| External cache pointer | Redis allowed as optimization pointer. Miss/error must skip optimization. | Gemini explicit cache names |
| Process-local cache | Allowed only for tiny stale windows where cross-worker invalidation is not required. | Firebase UID mapping, 60s TTL |
| Required transient state | Not cache. Either fail fast with clear health checks or move to durable storage. | Meal suggestion sessions |
| Correctness-critical writes | Do not cache. Persist first, then invalidate derived reads. | Meal writes, metric updates, notification dispatch |

## Consequences

Positive:

- Redis outage should make optional paths slower or more expensive, not incorrect.
- New cache proposals have a clear admission bar.
- Source-of-truth ownership stays explicit.
- Notification and FCM correctness stays database-owned.
- Cache bugs are easier to reason about because each key has a bounded stale window and invalidation path.

Trade-offs:

- Some repeated DB reads will remain uncached until measured pain exists.
- Engineers must write down cache ownership and invalidation before adding a key.
- Some low-risk performance wins may be delayed in favor of correctness.
- Required transient state remains an availability dependency until moved to durable storage.

## Current Guidance

Keep:

- Redis for food search/details when stale data is acceptable.
- Redis for nutrition lookup where expensive lookup chains justify it.
- Redis for Gemini cache names as cost optimization only.
- Short-TTL computed read caches only where mutation invalidation is already wired.
- Process-local auth UID cache with a small TTL.

Avoid:

- Redis for notification precompute data.
- Redis for FCM token ownership.
- Redis for meal writes, metric updates, and write-path correctness.
- Broad new user-scoped caches without measured need.
- Production `KEYS`; use deterministic keys, indexes, or `SCAN` as a bounded fallback.

Revisit:

- Move meal suggestion sessions to durable storage with `expires_at` if Redis reliability, command volume, or operational clarity becomes painful.
- Replace broad pattern invalidation with exact keys or versioned user namespaces if Redis command volume grows.
- Add per-key-family metrics before expanding cache usage.

## Alternatives Considered

### Cache More Aggressively

Rejected. It optimizes the easy part and pushes risk into invalidation, stale reads, and Redis command volume. This backend has user-specific nutrition, timezone, notification, and entitlement logic where stale correctness bugs are more expensive than a few DB reads.

### Disable Redis Broadly

Rejected. Redis is still useful for food lookup, nutrition lookup, short-lived read models, and AI-cost optimization. Removing it entirely would trade architecture clarity for unnecessary latency and cost.

### Treat Redis As A General Session Store

Rejected as a default. Redis can temporarily hold meal suggestion sessions, but that must be documented as required transient state. If the feature must survive Redis outage or restart, move it to the database.

## Validation Criteria

Before approving any new cache key, the reviewer should be able to answer:

- What is the source of truth?
- What exact stale window is acceptable?
- What invalidates it?
- What happens if Redis is down?
- How many Redis commands does this add at expected user count?
- Is this cache, a computed read model, an external pointer, or required state?

If those answers are not concrete, do not cache it.

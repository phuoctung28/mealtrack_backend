# Phase 04: Cache Invalidation Latency Decision

## Context Links

- [Plan overview](./plan.md)
- `docs/decisions/260608-2223-selective-cache-admission-policy.md`
- `docs/journals/260610-async-boundary-hygiene.md`
- `src/app/services/cache_invalidation_service.py`

## Overview

**Priority:** P2
**Status:** Planned

Decide whether to batch Redis invalidation based on production timing evidence,
not speculation.

## Key Insights

- Manual save already logs `db_ms`, `cache_ms`, and `total_ms`.
- Current invalidation is conservative and synchronous to prevent stale immediate
  reads after writes.
- The known risk is 6-8 sequential Redis round-trips on write paths.

## Requirements

- Preserve correctness for immediate post-write GETs.
- Do not convert required freshness into eventually consistent cache behavior
  without explicit product approval.
- Use production timing before optimizing.

## Architecture

Current path:

```text
command handler commits -> synchronous CacheInvalidationService -> response
```

Potential optimized path:

```text
command handler commits -> Redis pipeline/UNLINK for safe key groups -> response
```

## Related Code Files

Potential future modifications:
- `src/app/services/cache_invalidation_service.py`
- `src/infra/cache/cache_service.py`
- `src/infra/cache/redis_client.py`
- Tests around meal, hydration, movement, and macro write invalidation

## Implementation Steps

1. Collect production logs for `manual_save handler timing` and
   `cache_invalidation timing`.
2. If `cache_ms` is consistently above 50 ms, design batched invalidation.
3. Batch exact keys first; handle patterns carefully.
4. Prefer `UNLINK` when supported for delete-heavy paths.
5. Keep fallback behavior correct when Redis errors.

## Todo List

- [ ] Gather production timing sample.
- [ ] Decide go/no-go for batching.
- [ ] Identify exact keys safe to batch.
- [ ] Add tests for stale-read prevention.
- [ ] Implement only if evidence supports it.

## Success Criteria

- `cache_ms` improves or remains bounded.
- Immediate post-write reads do not return stale derived values.
- Redis command volume does not grow.

## Risk Assessment

- Medium: batching can accidentally weaken invalidation if patterns are mishandled.
- Mitigation: write tests around each mutation family before changing behavior.

## Security Considerations

Cache keys must remain user-scoped. Do not log full key families if they expose
PII beyond user IDs already used in controlled backend logs.

## Next Steps

If no production latency issue appears, leave the current correctness-first path
unchanged.


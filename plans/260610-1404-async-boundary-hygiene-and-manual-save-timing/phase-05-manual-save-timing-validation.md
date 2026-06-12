---
phase: 5
title: "Manual save timing validation"
status: complete
priority: P1
effort: "1-2d"
dependencies: [1]
---

# Phase 5: Manual Save Timing Validation

## Context Links

- `src/api/routes/v1/meals.py`
- `src/app/handlers/command_handlers/create_manual_meal_command_handler.py`
- `src/app/services/cache_invalidation_service.py`
- `src/infra/cache/redis_client.py`
- `tests/unit/api/test_routes_with_mocked_event_bus.py`

## Overview

Prove where `/v1/meals/manual` waits before changing behavior. The current code is async, but mobile loading can still be backend-caused by DB commit, cache invalidation, Redis pattern scan, response handling, or mobile follow-up reads.

## Key Insights

- Manual meal route awaits event bus and returns only after handler completes.
- Handler commits via UoW then awaits cache invalidation before response.
- Cache invalidation does pattern deletes and key deletes; Redis latency can make a POST feel stuck.
- A prior fast `422` on this endpoint meant schema validation, but the current symptom is loading, so timing matters more than payload shape until logs say otherwise.

## Requirements

- Functional: capture timing for route start/end, event bus send, handler process, DB save/commit, and cache invalidation.
- Functional: verify success, validation error, DB error, Redis error, and slow Redis paths.
- Functional: produce a recommendation only after timing evidence.
- Non-functional: instrumentation must not leak sensitive payload or tokens.

## Architecture

Use structured logging or lightweight timing helper around existing boundaries. Prefer tests with fake cache/UoW delays to prove the timing labels. Do not change cache invalidation semantics until evidence identifies it as the bottleneck.

## Related Code Files

- Modify: `src/api/routes/v1/meals.py`
- Modify: `src/app/handlers/command_handlers/create_manual_meal_command_handler.py`
- Modify: `src/app/services/cache_invalidation_service.py`
- Modify tests: `tests/unit/api/test_routes_with_mocked_event_bus.py`
- Modify/Create tests: `tests/unit/handlers/command_handlers/test_create_manual_meal_command_handler.py` if absent
- Optional read: mobile repo only if backend timing shows POST returns quickly

## Implementation Steps

1. Tests before: add unit test with delayed cache invalidation proving handler waits before response.
2. Add timing logs/metrics around manual save route and handler boundaries.
3. Add cache invalidation timing for each key/pattern family.
4. Run local targeted manual-save tests with fake slow cache.
5. If backend POST is slow, decide between timeout, bounded invalidation, async secondary invalidation, or Redis pattern redesign.
6. If backend POST is fast, hand off to mobile diagnosis with exact backend timing evidence.
7. Do not alter response contract without separate approval.

## Success Criteria

- [x] Manual save timing shows where latency occurs.
- [x] Slow cache path is test-covered.
- [x] Logs contain safe IDs and elapsed milliseconds, not full meal payloads or auth data.
- [x] Recommendation says backend fix vs mobile follow-up with evidence.
- [x] No speculative cache behavior change ships without timing proof.

## Risk Assessment

Risk: logging adds noise or PII. Mitigation: log safe IDs, phase labels, elapsed milliseconds only.

Risk: fixing perceived spinner by making invalidation fire-and-forget reintroduces stale-read race. Mitigation: any async invalidation split must preserve critical keys or add read-after-write versioning.

## Security Considerations

No auth changes. Avoid logging food payload details, Firebase tokens, or raw request body.

## Next Steps

Use evidence to choose a backend fix plan or mobile diagnosis plan. Keep separate from generic async cleanup unless the timing proves overlap.

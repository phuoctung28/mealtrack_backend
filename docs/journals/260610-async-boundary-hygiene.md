# Async Boundary Hygiene and Manual Save Timing

**Date**: 2026-06-10 14:53
**Severity**: High
**Component**: Event bus, UoW, feature flags, AI meal generation, manual save route
**Status**: Resolved (PR #339)

## What Happened

The codebase had accumulated a set of async anti-patterns that had been individually patched but never systematically enforced. Bare `asyncio.create_task` in the event bus, `run_until_complete` inside a service method, and `db.commit()` sprinkled directly in route handlers all existed simultaneously. This session closed the loop: added static guardrails so they can't come back, then removed the offenders.

## The Brutal Truth

The sync `MealGenerationService.generate_meal_plan()` drove its own event loop with `get_event_loop().run_until_complete()` from inside an already-running async context. This is the kind of thing that works in dev, explodes on a production ASGI worker, and leaves you staring at "There is no current event loop in thread" at 2am with no obvious call stack. It was sitting there, abstract method and all, until now.

The feature flag routes were doing direct `await db.commit()` — bypassing the UoW entirely and raising `HTTPException` from what should be a domain-layer service. Code review caught that the exceptions leaked HTTP semantics into the service layer; flipped to `ConflictException` and `ResourceNotFoundException` before merge.

## Technical Details

**Phase 1 — Guardrails** (`tests/architecture/test_async_boundary_hygiene.py`):
- 4 static AST/grep-style tests; all allowlists start empty
- Catches: `await db.commit()` in routes, `run_until_complete`/`get_event_loop`/`set_event_loop` in src, bare `asyncio.create_task` in routes + event bus, `uow.session.commit()` outside UoW internals
- Zero known offenders remain — tests would have failed on the old code

**Phase 2 — BackgroundTaskManager**:
- `src/infra/event_bus/background_task_manager.py`: `spawn()`, `drain()`, `cancel_all()`
- `src/api/dependencies/task_manager.py`: process-wide singleton accessor for lifespan-owned task manager
- `PyMediatorEventBus.publish()` migrated from bare `asyncio.create_task` to `task_manager.spawn()`
- Lifespan in `main.py`: creates manager on startup, calls `drain()` on shutdown
- Critical fix: `drain()` must `await task.cancel()` then `await asyncio.gather(*tasks, return_exceptions=True)` before `engine.dispose()` — without the gather, the engine can be disposed while cancelled tasks are still cleaning up, causing connection-pool errors on shutdown

**Phase 3 — Transaction cleanup**:
- `src/app/services/feature_flag_service.py`: UoW-backed create/update; raises `ConflictException`/`ResourceNotFoundException`, not `HTTPException` — service layer must not know it is being called over HTTP
- `feature_flags.py` write routes now delegate entirely to `FeatureFlagService`
- `update_custom_macros_command_handler.py`: removed redundant `await uow.session.commit()` — UoW context manager's `__aexit__` already commits

**Phase 4 — Sync wrapper removal**:
- `MealGenerationService.generate_meal_plan()` sync method deleted
- Abstract sync stub removed from `MealGenerationServicePort`
- 3 resilience tests migrated to async

**Phase 5 — Manual save timing**:
- Structured logs in `meals.py`, `create_manual_meal_command_handler.py`, `cache_invalidation_service.py`
- Keys: `manual_save timing`, `manual_save handler timing`, `cache_invalidation timing` with `db_ms`, `cache_ms`, `total_ms`
- Finding: **6–8 sequential Redis round-trips per manual save** — each cache key invalidated one at a time
- Nominal: 10–25ms; cold-start Redis or network jitter: 100–300ms
- Recommendation: batch with `pipeline()`/`UNLINK` if `cache_ms > 50ms` appears consistently in production logs

## What We Tried

Nothing was tried and discarded here — the phases were sequential and each one landed. The only mid-course correction was the domain-exception fix on `FeatureFlagService` caught during review before merge.

## Root Cause Analysis

No single root cause — this was accumulated async technical debt from iterative patching. The immediate trigger was the event loop mismatch fix in the prior commit (`0b82e44`) which drew attention to the broader pattern. The lack of static enforcement meant each fix was local: the next feature could re-introduce bare `create_task` or direct `db.commit()` without any test catching it.

## Lessons Learned

- **Static guardrails first.** If a pattern is banned, write the architecture test before removing the offenders — then the removal is just "make the test pass." Doing it the other way means the pattern can silently return.
- **drain() is not optional.** Bare `asyncio.create_task` with no shutdown drain means background tasks are orphaned on every graceful restart. The manager pattern costs almost nothing and makes shutdown deterministic.
- **Service layer must not import HTTPException.** If a service raises `HTTPException`, it has leaked its caller's transport protocol into the domain. Caught by review here; worth adding a static test for it.
- **Sequential Redis calls compound.** 6–8 round-trips looks fine in unit tests (mocked). The timing logs will show it in production. Add the pipeline batch before this becomes a latency complaint, not after.

## Next Steps

- [ ] Monitor `cache_ms` in production logs; if consistently > 50ms, batch `cache_invalidation_service.py` with `pipeline()`/`UNLINK` — owner: backend team, trigger: first week of production data
- [ ] Consider adding a static architecture test that blocks `HTTPException` imports in `src/app/` and `src/domain/` layers
- [ ] PR #339 merge when delivery CI is green: https://github.com/phuoctung28/mealtrack_backend/pull/339

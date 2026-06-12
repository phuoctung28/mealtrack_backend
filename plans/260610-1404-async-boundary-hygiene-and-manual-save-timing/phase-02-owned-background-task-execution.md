---
phase: 2
title: "Owned background task execution"
status: complete
priority: P1
effort: "2-3d"
dependencies: [1]
---

# Phase 2: Owned Background Task Execution

## Context Links

- [Asyncio usage research](./research/asyncio-usage-research.md)
- [Red team review](./reports/from-planner-to-user-red-team-async-boundary-plan-review-report.md)
- `src/infra/event_bus/pymediator_event_bus.py`
- `src/api/routes/v1/meal_suggestions.py`

## Overview

Replace unowned fire-and-forget task spawning with explicit ownership. Event subscribers and request side effects must be tracked, drained, or intentionally non-critical.

## Key Insights

- Do not turn all domain-event subscribers into inline awaits; that can increase request latency.
- A managed runner can keep current asynchronous behavior while making failures observable and shutdown sane.
- Unsplash download tracking is non-critical; it can be best-effort but still should not leak exceptions.

## Requirements

- Functional: event bus background subscriber tasks are tracked and can be drained/cancelled on shutdown.
- Functional: subscriber exceptions are logged with event/subscriber context.
- Functional: request-local Unsplash tracking is moved behind owned helper or explicit best-effort adapter.
- Non-functional: default event bus behavior remains non-blocking for fire-and-forget domain events.

## Architecture

Add a small background task manager owned by the composition root or event bus. It exposes `spawn(name, coro)` and `shutdown()`/`drain()` behavior. Event bus uses it instead of raw `asyncio.create_task`. For route side effects, use the same manager or an adapter method that awaits with short timeout if compliance matters.

## Related Code Files

- Modify: `src/infra/event_bus/pymediator_event_bus.py`
- Modify/Create: `src/infra/event_bus/background_task_manager.py`
- Modify: `src/api/main.py`
- Modify: `src/api/routes/v1/meal_suggestions.py`
- Modify tests: `tests/unit/infra/event_bus/` or existing event bus tests
- Modify tests: `tests/unit/api/test_discover_parallel_images.py` if route side effect behavior changes

## Implementation Steps

1. Tests before: prove `publish()` schedules subscriber work through an injected manager and captures exceptions.
2. Tests before: prove shutdown drains or cancels outstanding subscriber tasks.
3. Implement minimal task manager with bounded surface: spawn, drain, cancel all.
4. Wire event bus to use manager; preserve current `publish()` return semantics.
5. Move Unsplash download trigger through managed path or await a short best-effort call with timeout.
6. Update architecture guard to remove event bus and route `create_task` allowlist entries.
7. Run targeted event bus and meal suggestion route tests.

## Success Criteria

- [x] No unmanaged `asyncio.create_task` remains in API route or event bus code.
- [x] Event subscriber failures are observable in tests.
- [x] Event bus `publish()` remains non-blocking unless explicitly configured otherwise.
- [x] App shutdown can cancel/drain managed tasks without unhandled warnings.

## Risk Assessment

Risk: managed tasks still die after response and lose critical work. Mitigation: classify subscribers; critical data writes must not rely on best-effort background execution.

Risk: event bus lifetime wiring gets complex. Mitigation: one small manager injected at composition root, no new queue framework.

## Security Considerations

Background task errors can include user identifiers. Logs should include event type and safe IDs, not secrets or tokens.

## Next Steps

Phase 3 cleans transaction/session bypasses once async task ownership is safer.

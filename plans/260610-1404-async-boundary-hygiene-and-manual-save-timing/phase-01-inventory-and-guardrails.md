---
phase: 1
title: "Inventory and guardrails"
status: complete
priority: P1
effort: "1-2d"
dependencies: []
---

# Phase 1: Inventory and Guardrails

## Context Links

- [Runtime boundary inventory](./research/runtime-boundary-inventory.md)
- [Asyncio usage research](./research/asyncio-usage-research.md)
- `tests/architecture/test_async_db_runtime_boundaries.py`
- `docs/system-architecture.md`

## Overview

Create the safety net before cleanup. Extend existing architecture tests so new route-level commits, unmanaged task creation, and event-loop-driving sync wrappers cannot expand.

## Key Insights

- Existing async DB guard passes, so this phase should add narrow checks, not reopen migration.
- Guardrails must distinguish legitimate sync SDK off-loop calls from bad sync compatibility wrappers.
- File naming debt is lower risk than runtime behavior debt.

## Requirements

- Functional: detect direct `await db.commit()` in active API routes unless explicitly allowlisted.
- Functional: detect `run_until_complete`, `asyncio.get_event_loop`, and `asyncio.set_event_loop` in runtime source.
- Functional: detect unmanaged `asyncio.create_task` in request/event bus paths unless owned by a managed runner.
- Non-functional: tests are static and fast; no external services.

## Architecture

Extend architecture tests as static AST/text checks. Keep existing async DB boundary test intact. Add separate test names for transaction ownership and task ownership so failures point to the real contract.

## Related Code Files

- Modify: `tests/architecture/test_async_db_runtime_boundaries.py`
- Modify: `tests/architecture/` new or existing guard file if current file grows too large
- Read: `src/api/routes/v1/feature_flags.py`
- Read: `src/api/routes/v1/meal_suggestions.py`
- Read: `src/infra/event_bus/pymediator_event_bus.py`
- Read: `src/infra/adapters/meal_generation_service.py`

## Implementation Steps

1. Add tests for forbidden event-loop driving in `src/` runtime files.
2. Add tests for direct `await db.commit()` in route modules, with short allowlist only if a phase intentionally defers a route.
3. Add tests for unmanaged `asyncio.create_task` in API routes and event bus code.
4. Add tests for direct `uow.session.commit()` outside UoW internals.
5. Run new architecture tests first and record expected failures.
6. Keep allowlists explicit and shrinking. No broad directory exclusions.

## Success Criteria

- [x] Targeted architecture test fails on current known offenders.
- [x] Allowlist entries match only deferred cleanup targets.
- [x] Existing async DB runtime boundary test still passes.
- [x] No product code changed in this phase except test-only helpers if needed.

## Risk Assessment

Risk: guardrails too strict block legitimate vendor SDK wrappers. Mitigation: test exact anti-patterns, not all `to_thread`.

Risk: one giant architecture file becomes hard to read. Mitigation: split into focused test module if needed.

## Security Considerations

Guardrails reduce hidden background failures and route-level transaction drift. No auth or data exposure changes.

## Next Steps

Phase 2 removes or owns task creation offenders.

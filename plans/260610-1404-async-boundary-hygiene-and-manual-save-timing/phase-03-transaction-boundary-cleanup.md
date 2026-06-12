---
phase: 3
title: "Transaction boundary cleanup"
status: complete
priority: P1
effort: "2-3d"
dependencies: [1]
---

# Phase 3: Transaction Boundary Cleanup

## Context Links

- [Runtime boundary inventory](./research/runtime-boundary-inventory.md)
- `src/api/routes/v1/feature_flags.py`
- `src/api/routes/v1/meal_suggestions.py`
- `src/app/handlers/command_handlers/update_custom_macros_command_handler.py`
- `src/infra/database/uow_async.py`

## Overview

Move remaining write transaction ownership out of routes and direct session calls. Keep reads stable unless a handler/repository already exists.

## Key Insights

- Direct `AsyncSession` is not sync DB debt, but route-level writes bypass CQRS and UoW conventions.
- `uow.session.commit()` inside a handler is stronger drift than `await uow.commit()`.
- UoW fail-fast re-entry should be deferred until handler reuse tests prove safe.

## Requirements

- Functional: feature flag create/update writes move behind command handlers or an application service using UoW.
- Functional: meal suggestion pending queue enqueue commit moves out of route or uses UoW-owned repository boundary.
- Functional: `update_custom_macros` uses UoW transaction ownership, not `uow.session.commit()`.
- Non-functional: no public API response shape change.

## Architecture

Routes construct commands/queries and delegate. UoW owns commit/rollback through context manager or explicit UoW method only where current handlers already use that pattern. Repository methods flush but do not commit.

## Related Code Files

- Modify: `src/api/routes/v1/feature_flags.py`
- Create/Modify: `src/app/commands/feature_flags/*` if no existing command exists
- Create/Modify: `src/app/handlers/command_handlers/feature_flags/*`
- Modify: `src/api/routes/v1/meal_suggestions.py`
- Modify: `src/api/dependencies/meal_image_cache.py` if pending queue ownership moves there
- Modify: `src/app/handlers/command_handlers/update_custom_macros_command_handler.py`
- Modify tests: feature flag route tests, meal suggestion discovery tests, custom macros handler tests

## Implementation Steps

1. Tests before: add route/handler tests that capture current feature flag create/update behavior.
2. Tests before: add custom macros test proving commit/rollback ownership through UoW.
3. Implement feature flag command/handler or app service with UoW transaction.
4. Refactor feature flag route to delegate and stop calling `db.commit()`.
5. Refactor pending image enqueue commit path so route does not own transaction.
6. Replace `uow.session.commit()` in custom macros handler with UoW-owned boundary.
7. Update static guard allowlists from Phase 1.
8. Run targeted route and handler tests.

## Success Criteria

- [x] No `await db.commit()` remains in active route modules.
- [x] No `await uow.session.commit()` remains outside UoW internals.
- [x] Feature flag API behavior unchanged.
- [x] Meal suggestion discovery still enqueues pending image misses.
- [x] Existing async DB architecture guard still passes.

## Risk Assessment

Risk: feature flag route currently simple; adding CQRS could over-engineer. Mitigation: use minimal command/handler or app service, no generic framework.

Risk: meal suggestion route has dense orchestration. Mitigation: move only transaction boundary, not full route rewrite.

## Security Considerations

Feature flag admin dependency must remain unchanged. Do not weaken `require_admin`.

## Next Steps

Phase 4 removes sync compatibility wrappers after transaction ownership is stable.

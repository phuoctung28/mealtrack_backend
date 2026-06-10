---
type: research
title: "Runtime boundary inventory"
created: "2026-06-10"
---

# Runtime Boundary Inventory

## Summary

App DB runtime is async. Remaining cleanup is boundary hygiene: direct route sessions, manual commits, misleading compatibility names, and sync SDK calls inside async flows.

## Findings

- Async runtime baseline exists: `src/infra/database/config_async.py:67` resolves app DB policy and creates async engine/session factory.
- Migration/admin sync engine remains intentionally isolated: `src/infra/database/config.py:1` says app runtime uses `config_async.py`.
- Runtime guard exists: `tests/architecture/test_async_db_runtime_boundaries.py:62` blocks sync DB imports outside the migration config.
- Route-level DB bypass remains: `src/api/routes/v1/feature_flags.py:33` injects `AsyncSession`; writes commit in route at `src/api/routes/v1/feature_flags.py:130` and `src/api/routes/v1/feature_flags.py:180`.
- Meal suggestion discovery mixes route DB session with service work: `src/api/routes/v1/meal_suggestions.py:68` injects `AsyncSession`; pending image enqueue commits at `src/api/routes/v1/meal_suggestions.py:165`.
- Handler transaction drift remains: `src/app/handlers/command_handlers/update_custom_macros_command_handler.py:51` calls `uow.session.commit()` directly.
- Compatibility dependency remains: `src/api/base_dependencies.py:81` exposes `get_db()` but yields async sessions.
- Async-named repository consistency is incomplete but lower risk: `src/infra/repositories/promo_code_repository.py:11` and `src/infra/repositories/referral_repository.py:19` are async despite non-async filenames.

## Recommendation

Do not reopen the full async repository migration. Keep this plan focused on active async-boundary cleanup and add guardrails so new route-level commits, unmanaged tasks, and event-loop-driving sync wrappers do not return.

## Unresolved Questions

None.

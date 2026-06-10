---
phase: 3
title: "Request Path Dependency Migration"
status: completed
priority: P1
effort: "4-6 days"
dependencies: [2]
---

# Phase 3: Request Path Dependency Migration

## Overview

Remove sync DB dependencies from FastAPI request paths while preserving API behavior.

## Requirements

- Functional: request handlers and dependencies use async DB sessions/UoW.
- Functional: route behavior for meals, meal suggestions, feature flags, auth, ingredients, and image cache remains compatible.
- Non-functional: no sync DB blocking in async request handlers.

## Architecture

FastAPI dependencies should use `get_async_db` or services built from `AsyncUnitOfWork`. Event bus handlers should keep receiving fresh `AsyncUnitOfWork` instances.

## Related Code Files

- Modify: `src/api/base_dependencies.py`
- Modify: `src/api/dependencies/auth.py`
- Modify: `src/api/dependencies/event_bus.py`
- Modify: `src/api/dependencies/meal_image_cache.py`
- Modify: `src/api/routes/v1/meal_suggestions.py`
- Modify: `src/api/routes/v1/feature_flags.py`
- Modify: `src/app/handlers/query_handlers/get_meals_by_date_query_handler.py`
- Modify: `src/app/handlers/command_handlers/create_manual_meal_command_handler.py`
- Modify: route tests under `tests/unit/api/` and `tests/integration/routes/`

## Implementation Steps

1. Replace sync route dependencies with async equivalents.
2. Remove direct `MealRepository` sync injection from request handlers.
3. Fix handlers that mix async UoW for timezone resolution with sync injected repositories.
4. Replace profile-provider sync session usage with async UoW/provider.
5. Update meal suggestion route/service dependencies without changing response shape.
6. Run targeted route and handler tests.

## Success Criteria

- [x] Static guard test finds no sync DB imports in request-path files except transition allowlist removed by phase end.
- [x] Meal creation/read routes preserve behavior.
- [x] Meal suggestion routes preserve behavior.
- [x] Feature flag routes preserve behavior.
- [x] Auth dependency remains compatible.

## Progress Notes

- Migrated `src/api/routes/v1/feature_flags.py` from sync `Session`/`query()` to `AsyncSession`/`select()`.
- Updated `tests/unit/api/test_feature_flags_routes.py` to override `get_async_db` with async-session-shaped mocks.
- Removed `src/api/routes/v1/feature_flags.py` from the sync DB runtime transition allowlist in `tests/architecture/test_async_db_runtime_boundaries.py`.
- Migrated `src/api/dependencies/meal_image_cache.py` and `src/api/routes/v1/meal_suggestions.py` to `get_async_db`.
- Added explicit `db.commit()` ownership in the meal suggestion route after pending queue writes.
- Replaced the suggestion orchestration profile provider with an async UoW-backed provider; sync providers remain supported for tests.
- Migrated the barcode lookup handler's local food-reference cache reads/writes to short async UoW scopes in production event-bus wiring.
- Migrated nutrition lookup and ingredient resolver singleton wiring to an async UoW-backed food-reference adapter.
- Migrated DeepL meal translation singleton wiring to an async UoW-backed meal-translation adapter.
- Migrated referral credit/revoke webhook helpers to use `AsyncUnitOfWork.referrals` instead of constructing repositories from the request UoW session.
- Migrated FastAPI startup database warming from the sync engine to `async_engine`.
- Converted the legacy `src.api.base_dependencies.get_db` compatibility symbol to delegate to `get_async_db`, removing the last request-path sync DB config import.
- Converted the legacy food-reference getter aliases in `src.api.base_dependencies` to return the async UoW adapter.
- Final validation removed the request-path sync DB import transition allowlist, preserved auth dependency compatibility, and passed the full pytest suite.

## Risk Assessment

Risk: `src/api/base_dependencies.py` is wide and easy to break.

Mitigation: change one dependency group at a time and run focused tests after each group.

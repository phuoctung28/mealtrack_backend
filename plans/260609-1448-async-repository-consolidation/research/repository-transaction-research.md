---
type: researcher-report
created: 2026-06-09 14:48
topic: async repository consolidation transaction boundaries
status: complete
---

# Repository Transaction Research

## Summary

The repository layer has two separate problems:

- contract mismatch: sync-shaped ports are implemented by async repositories;
- transaction mismatch: sync repositories often commit internally while async repositories mostly leave commit/rollback to `AsyncUnitOfWork`.

The plan must fix both. Only renaming files from sync to async will not solve the real issue.

## Findings

### Repositories Already Async and Non-Committing

- `src/infra/repositories/meal_repository_async.py`
- `src/infra/repositories/user_repository_async.py`
- `src/infra/repositories/subscription_repository_async.py`
- `src/infra/repositories/weekly_budget_repository_async.py`
- `src/infra/repositories/saved_suggestion_db_repository_async.py`
- `src/infra/repositories/cheat_day_repository_async.py`
- `src/infra/repositories/notification_repository_async.py`
- `src/infra/repositories/hydration_repository_async.py`
- `src/infra/repositories/movement_repository_async.py`
- `src/infra/repositories/weight_repository_async.py`
- `src/infra/repositories/referral_repository.py`
- `src/infra/repositories/promo_code_repository.py`

### Sync Repositories With Internal Transaction Ownership

- `src/infra/repositories/meal_repository.py`
- `src/infra/repositories/user_repository.py`
- `src/infra/repositories/subscription_repository.py`
- `src/infra/repositories/weekly_budget_repository.py`
- `src/infra/repositories/saved_suggestion_db_repository.py`
- `src/infra/repositories/notification_repository.py`
- `src/infra/repositories/food_reference_repository.py`
- `src/infra/repositories/meal_translation_repository.py`
- `src/infra/repositories/pending_meal_image_repository.py`
- `src/infra/repositories/pgvector_meal_image_cache_repository.py`
- notification operation helpers under `src/infra/repositories/notification/`

### Port Mismatch

The most visible mismatch is `MealRepositoryPort`, which has sync abstract methods while `AsyncMealRepository` exposes async methods. Similar checks are needed for user, subscription, saved suggestion, notification, and meal suggestion ports.

### Test Mismatch

Tests use helpers that make sync repositories awaitable:

- `AsyncSyncRepoWrapper` in `tests/conftest.py`
- local wrappers in delete-user tests
- sync repository fixtures for repository tests

These wrappers are useful during transition but must not survive final async-only runtime.

## Recommended Migration Shape

- Convert ports or introduce explicit async ports before deleting sync implementations.
- Use async repositories as the canonical implementations.
- Keep repository transaction behavior uniform: `flush()` inside repositories when needed, `commit()` only in UoW or dependency boundary.
- Rewrite tests to use async fixtures instead of awaitable wrappers around sync code.
- Delete sync repositories after consumers and tests move.

## Unresolved Questions

None.

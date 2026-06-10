---
type: implementation-report
created: 2026-06-09
phase: 1
status: complete
---

# Phase 1 Inventory

## Summary

Phase 1 found and pinned the current sync DB boundary before larger migration work starts.

## Sync Runtime Import Allowlist

These files still import sync database config, sync `UnitOfWork`, or sync SQLAlchemy `Session` and must be migrated in later phases:

- `src/api/base_dependencies.py`
- `src/api/dependencies/meal_image_cache.py`
- `src/api/main.py`
- `src/api/routes/v1/feature_flags.py`
- `src/api/routes/v1/health.py`
- `src/api/routes/v1/meal_suggestions.py`
- `src/cron/email.py`
- `src/cron/push.py`
- `src/infra/database/uow.py`
- `src/infra/repositories/base.py`
- `src/infra/repositories/cheat_day_repository.py`
- `src/infra/repositories/food_reference_repository.py`
- `src/infra/repositories/meal_repository.py`
- `src/infra/repositories/meal_translation_repository.py`
- `src/infra/repositories/notification/fcm_token_operations.py`
- `src/infra/repositories/notification/notification_preferences_operations.py`
- `src/infra/repositories/notification/reminder_query_builder.py`
- `src/infra/repositories/notification_repository.py`
- `src/infra/repositories/pending_meal_image_repository.py`
- `src/infra/repositories/pgvector_meal_image_cache_repository.py`
- `src/infra/repositories/saved_suggestion_db_repository.py`
- `src/infra/repositories/subscription_repository.py`
- `src/infra/repositories/user_repository.py`
- `src/infra/repositories/weekly_budget_repository.py`
- `src/infra/services/cron_notification_dispatch_service.py`
- `src/infra/services/cron_trial_push_service.py`
- `src/infra/services/daily_context_precompute_service.py`

## Repository Transaction Allowlist

These repository files still call `commit()` or `rollback()` internally and must be migrated later:

- `src/infra/repositories/food_reference_repository.py`
- `src/infra/repositories/meal_repository.py`
- `src/infra/repositories/meal_translation_repository.py`
- `src/infra/repositories/notification/fcm_token_operations.py`
- `src/infra/repositories/notification/notification_preferences_operations.py`
- `src/infra/repositories/notification_repository.py`
- `src/infra/repositories/pending_meal_image_repository.py`
- `src/infra/repositories/pgvector_meal_image_cache_repository.py`
- `src/infra/repositories/saved_suggestion_db_repository.py`
- `src/infra/repositories/subscription_repository.py`
- `src/infra/repositories/user_repository.py`
- `src/infra/repositories/weekly_budget_repository.py`

## Base Split

`Base` now lives in `src/infra/database/base.py`. ORM models, migrations, and tests import it from that neutral module instead of sync runtime config.

## Unresolved Questions

None.

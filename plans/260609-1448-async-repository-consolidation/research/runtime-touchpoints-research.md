---
type: researcher-report
created: 2026-06-09 14:48
topic: async repository consolidation runtime touchpoints
status: complete
---

# Runtime Touchpoints Research

## Summary

Runtime sync DB usage is not isolated to legacy repositories. It appears in cron entrypoints, FastAPI dependencies, meal suggestion route dependencies, feature flag routes, image-cache dependencies, health checks, and profile providers.

Hard truth: deleting sync repositories before these consumers are moved will break runtime. Convert consumers first, then delete providers.

## Findings

### Sync DB Config Consumers

Files using `src.infra.database.config`, `SessionLocal`, `ScopedSession`, `get_db`, or sync `Session` in runtime paths:

- `src/api/base_dependencies.py`
- `src/api/routes/v1/meal_suggestions.py`
- `src/api/routes/v1/feature_flags.py`
- `src/api/dependencies/meal_image_cache.py`
- `src/api/routes/v1/health.py`
- `src/cron/push.py`
- `src/cron/email.py`
- `src/infra/services/cron_trial_push_service.py`
- `src/infra/services/cron_notification_dispatch_service.py`
- `src/infra/services/daily_context_precompute_service.py`
- `src/domain/services/meal_suggestion/suggestion_orchestration_service.py`
- `src/domain/services/meal_suggestion/ingredient_nutrition_resolver.py`

### Existing Async Runtime Pattern

Most modern command/query handlers already use `AsyncUnitOfWork`, especially:

- hydration
- movement
- weight
- referral
- promo code
- saved suggestions
- user profile and metrics
- daily/weekly macro queries

Event bus setup already injects `AsyncUnitOfWork` for many handlers.

### Runtime Migration Order

1. Add async replacement dependencies while old sync path still exists.
2. Move route/service consumers one by one.
3. Move cron jobs after request path is stable.
4. Remove sync config only after runtime imports disappear.

## Risks

- `src.api.base_dependencies` mixes many dependency types. A broad edit can break unrelated services.
- Meal suggestion services use profile providers and food lookup paths that currently mention sync sessions.
- Health checks may use sync DB because it is simple; replacing them with async checks must preserve operational signal.
- Cron entrypoints may be called from scripts expecting sync functions.

## Recommendations

- Treat runtime migration as its own phase before deleting repository files.
- Add static guard tests that distinguish runtime sync imports from allowed migration/test imports.
- Keep Alembic/migration config discussion separate from runtime DB config.

## Unresolved Questions

None.

---
phase: 7
title: "Measurement And Controlled Rollout"
status: complete
priority: P1
effort: "3-5d"
dependencies: [6]
---

# Phase 7: Measurement And Controlled Rollout

## Overview

Add raw product measurement, safe operational telemetry, default-off gating, and controlled-launch verification.

## Context Links

- [Plan](./plan.md)
- Existing settings: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/config/settings.py`
- Existing flags: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/feature_flags.py`

## Key Insights

- PostHog adapter captures analytics but does not evaluate backend flags.
- Existing DB feature flags are boolean; cohort percentage needs a separately verified control path.

## Requirements

- Functional: default off; internal/cohort exposure; server-owned `plan_shown`, `alternatives_shown`, `swap_selected`, `meal_logged`; catalog/recommendation metrics.
- Non-functional: safe bounded attributes; feature correct during Redis/PostHog outage; no learned popularity cron yet.

## Architecture

Use `MEAL_RECOMMENDATIONS_ENABLED=false` as hard kill switch, then server-side internal allowlist and deterministic HMAC user bucketing for audited/versioned cohorts. PostHog is analytics-only and receives a versioned HMAC pseudonymous ID, never raw user identity or authorization control.

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/config/settings.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/base_dependencies.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/dependencies/event_bus.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/adapters/posthog_adapter.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/observability.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/monitoring/observability.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/test_meal_recommendation_feature_gate.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/services/meal_recommendation_cohort_service.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/meal_recommendations.py`

## Implementation Steps

1. Add default-false setting and gate create/swap/log entry points; authenticated owner-scoped reads of existing plans remain available.
2. Persist `plan_shown` and `alternatives_shown` when their API responses are successfully produced; persist swap/log events only with their committed transactions. Add no client event-ingestion endpoint.
3. Emit bounded metrics for generate latency/count, candidate counts, fallback stage, insufficiency, swap latency/conflict, precomputed hit, and logging conversion.
4. Run migration-head, architecture, compile, Ruff, lint-imports, unit/API/integration/concurrency, and catalog validation gates.
5. Load-test representative catalog against p95 targets: create <500 ms, read/swap <200 ms where precomputed.
6. Define PostHog versioned HMAC identity, consent/opt-out, property allowlists, retention/deletion, and forbidden-field tests; keep operational metrics anonymous.
7. Enable internal allowlist, then audited/versioned deterministic cohorts with fail-closed evaluation; review insufficiency, calorie deviation, swaps, logging conversion, and errors before expansion.

## Todo

- [x] Default-off behavior and fail-open analytics tested.
- [x] Privacy-safe metrics/events verified.
- [x] Controlled-launch checklist and rollback steps documented.

## Success Criteria

- [x] Focused CI-equivalent recommendation suite passes with a single Alembic head.
- [x] Existing AI suggestions route remains separate and unchanged by the gate.
- [x] Rollout can be disabled without data loss or Redis dependency.
- [ ] Representative-catalog p95/load and live PostgreSQL concurrency gates completed.

## Rollout Checklist

1. Keep `MEAL_RECOMMENDATIONS_ENABLED=false` until the production catalog corpus is installed.
2. Enable only internal IDs through `MEAL_RECOMMENDATIONS_INTERNAL_USER_IDS`.
3. Set `MEAL_RECOMMENDATIONS_COHORT_SALT` before any percentage rollout.
4. Set `MEAL_RECOMMENDATIONS_ANALYTICS_SALT` before PostHog capture; empty salt disables analytics.
5. Watch bounded metrics: request status, operation latency, disabled requests, conflicts, and log conversion.
6. Roll back by setting `MEAL_RECOMMENDATIONS_ENABLED=false`; reads of existing plans remain available.

## Validation Log

### Phase 7 Completion — 2026-07-16

- **Completed:** hard default-off backend gate, internal allowlist, deterministic HMAC cohort service, privacy-safe PostHog wrapper, bounded operational metrics for create/read/swap/log, and route tests for disabled/default-off behavior.
- **Verified:** percentage rollout fails closed without salt, analytics emits HMAC pseudonymous IDs only, analytics is skipped without salt, create/swap/log are gated, owner-scoped reads remain available, and import boundaries remain clean.
- **Tests:** `.venv/bin/python3.13 -m pytest -q tests/unit/infra/repositories/test_meal_recommendation_plan_repository_async.py tests/unit/app/handlers/test_meal_recommendation_handlers.py tests/unit/app/services/test_meal_recommendation_history_projector.py tests/unit/app/services/test_recommended_meal_materialization_service.py tests/unit/app/services/test_meal_recommendation_rollout_services.py tests/unit/api/test_meal_recommendations_route.py tests/migrations/test_alembic_revision_graph.py tests/migrations/test_catalog_recipe_tables_migration.py` passed with 44 tests.
- **Lint/type:** focused Ruff, targeted mypy, `.venv/bin/lint-imports`, and `git diff --check` passed.
- **Deferred validation:** representative production catalog p95/load testing and live PostgreSQL race harness remain blocked until Phase 3's real corpus and database harness are available.

## Risk Assessment

Misdescribed cohort control could expose broadly. Mitigation: hard backend boolean plus verified cohort mechanism before percentage rollout.

## Security Considerations

No user IDs, recipe names, ingredients, URLs, profile fields, or payloads in metrics/logs; ownership checks remain server-side.

## Next Steps

- Post-MVP only after measured volume: popularity aggregate/read model, Bayesian ranking, exploration, and measured cache.

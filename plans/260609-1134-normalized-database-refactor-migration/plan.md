---
title: "Normalized Database Refactor and Migration"
description: "Normalize MealTrack OLTP source-of-truth tables with backward-compatible migrations, ownership constraints, and phased read cutovers."
status: completed
priority: P1
effort: "5-8 weeks"
branch: "main"
tags: [backend, database, refactor, critical]
blockedBy: []
blocks: []
created: "2026-06-09T04:34:46.358Z"
createdBy: "ck:plan"
source: skill
---

# Normalized Database Refactor and Migration

## Overview

Normalize the backend database foundation over a 6-12 month scaling horizon without a risky rewrite. This plan follows `docs/standards/db-api.md`: OLTP source-of-truth tables target 3NF, user-owned rows get real FKs, JSON remains only for raw/audit/cache/temporary compatibility, and every data migration uses expand-migrate-contract.

Scope is code + migrations only. API responses stay backward compatible while repositories/mappers read normalized data first and fall back to legacy columns until cutover.

## Scope Challenge

- Existing code: SQLAlchemy/Alembic, async UoW, migration graph test, user/profile/meal/hydration/saved suggestion repositories, and cache invalidation already exist.
- Minimum safe change set: foundation, FK ownership, then the highest-risk JSON/overloaded domains. Daily read models wait until normalized sources are stable.
- Complexity: touches 8+ areas, so use sequential phases with clear rollback gates. Avoid parallel DB changes that compete for Alembic head and shared mappers.
- Selected mode: HOLD SCOPE, deep planning. Normalization is mandatory, but implementation remains incremental.

## Architecture Direction

Use expand-migrate-contract for every legacy shape:

1. Expand: add normalized tables/columns nullable and indexed.
2. Migrate: idempotent backfill from legacy rows, with orphan/malformed data handling.
3. Dual-write: write normalized and legacy shapes while old code/client paths exist.
4. Read cutover: read normalized first, fallback to legacy.
5. Contract: drop legacy JSON/columns only after production verification.

## Cross-Plan Dependencies

No unfinished project plan blocks this work. Existing Redis and AI reliability plans are completed.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Foundation and migration safety](./phase-01-foundation-and-migration-safety.md) | Completed |
| 2 | [User ownership constraints](./phase-02-user-ownership-constraints.md) | Completed |
| 3 | [Profile preference normalization](./phase-03-profile-preference-normalization.md) | Completed |
| 4 | [Hydration table migration](./phase-04-hydration-table-migration.md) | Completed |
| 5 | [Saved suggestion and recipe normalization](./phase-05-saved-suggestion-and-recipe-normalization.md) | Completed |
| 6 | [Food notification and payout normalization](./phase-06-food-notification-and-payout-normalization.md) | Completed |
| 7 | [Read cutover indexes and summaries](./phase-07-read-cutover-indexes-and-summaries.md) | Completed |
| 8 | [Release validation and rollout](./phase-08-release-validation-and-rollout.md) | Completed |

## Dependencies

- PostgreSQL/Neon remains the canonical database engine.
- Current Alembic head verified as `20260609000006`.
- Keep backend calorie derivation authoritative during all migrations.
- Mobile/API contracts remain compatible until explicit contract phase.

## Not In Scope

- Microservice split.
- Warehouse/OLAP buildout before OLTP cleanup.
- One-shot migration that drops legacy JSON in same release.
- Client-side calorie derivation or mobile contract break.

## Verification Plan

- `alembic heads`
- `alembic upgrade head`
- migration graph tests
- metadata registry tests
- targeted unit/integration tests per phase
- repository fallback tests for legacy + normalized rows
- delete-account/orphan cleanup tests for user-owned tables

## Unresolved Questions

Resolved in Validation Session 1:

- `saved_suggestions.user_id`: use `users.id` as canonical. Audit legacy rows first, repair any outliers, then add FK.
- Account deletion: cascade private logs/preferences/suggestions; retain or anonymize accounting/audit rows.
- Hydration calories: store macro/volume facts and derive calories in backend; expose `kcal` and `calories` as response aliases only.
- Production first deploy: production should be Alembic-only. Keep `Base.metadata.create_all()` only for tests/local tooling if needed.

## Validation Log

### 2026-06-09 Implementation Session 1

- Implemented phases 1-4.
- Added migrations `20260609000001`, `20260609000002`, and `20260609000003`.
- Verified focused suite: 32 tests passed.
- Verified Ruff on touched files: passed.
- Verified Alembic has one head: `20260609000003`.
- Phases 5-8 remain pending.

### 2026-06-09 Implementation Session 2

- Implemented phases 5-8.
- Added migrations `20260609000004`, `20260609000005`, and `20260609000006`.
- Saved suggestions now dual-write normalized header/items/steps and retain `suggestion_data` as compatibility snapshot.
- Meal recipes now dual-write `meal_instruction_steps` and keep `meal.instructions` as legacy compatibility.
- Food references now dual-write normalized serving sizes/nutrients and retain legacy JSON response shape.
- Payout requests now store typed workflow fields and retain raw `payment_details` pending a later security/contract pass.
- Notification context is documented as render snapshot; recipient truth remains normalized in `user_fcm_tokens`.
- Production migration runner is Alembic-only; it no longer creates schema from `Base.metadata` or stamps head.
- Verified focused suite: 32 tests passed.
- Verified Ruff on touched files: passed.
- Verified local Postgres upgrade to Alembic head `20260609000006`.

### 2026-06-09 Validation Session 1

#### Verification Results

- **Tier:** Full
- **Claims checked:** 62
- **Verified:** 59
- **Failed:** 0 after validation decisions
- **Resolved findings:** 1
- **Unverified:** 0 after validation decisions

Verified:

- `ck plan validate --strict` passed with 8 phases, 0 errors, 0 warnings.
- Current Alembic head/current revision is `20260531000001`.
- All 40 sampled existing file paths in phase inventories exist.
- `src/infra/database/models/__init__.py` currently does not import `MealImageCacheModel` or `PendingMealImageResolutionModel`.
- `migrations/env.py` currently uses `target_metadata = Base.metadata` without importing the central model registry first.
- Profile preference fields are JSON in `src/infra/database/models/user/profile.py` and map directly through `src/infra/mappers/user_mapper.py`.
- Hydration currently writes `Meal` rows with `meal_type="hydration"`, `source="hydration"`, placeholder `MealImage`, and `quantity` as credited ml.
- Hydration read paths currently use `uow.meals.find_by_date(...)`, `sum_hydration_ml_for_date(...)`, and `sum_hydration_ml_by_date_range(...)`.
- `saved_suggestions.user_id` is `String(128)`, `suggestion_data` is JSON, and `/v1/saved-suggestions` uses `get_current_user_id`.
- `get_current_user_id` resolves Firebase UID to `users.id`, so new saved-suggestion writes should already use `users.id`; old rows still need audit before adding FK.
- `food_reference.serving_sizes`, `food_reference.extra_nutrients`, `notifications.context`, and `payout_requests.payment_details` are JSON.
- `migrations/run.py` still has a first-deployment path using `Base.metadata.create_all(bind=engine)`, so the Alembic-only decision is real, not theoretical.

Resolved finding:

1. **Hydration calorie storage design** - Phase 4 proposes storing both `kcal` and `calories` on `hydration_entries`. That duplicates data and conflicts with the standards rule that backend-derived calories should come from macros. Recommendation: store drink volume, credited ml, and macro fields needed to derive calories; expose `kcal` and `calories` as response aliases only.

Unverified / needs product decision:

1. None after user confirmation.

#### Pending Validation Questions

Answered by user: yes to recommended choices.

1. `saved_suggestions.user_id`: canonical `users.id`; audit/fix legacy outliers before FK.
2. Account deletion: cascade private data; retain/anonymize accounting/audit rows.
3. Hydration calories: derive from stored macro fields and expose aliases.
4. First deploy: production Alembic-only; keep `create_all()` only for tests/local tooling if needed.

#### Whole-Plan Consistency Sweep

- Files reread: `plan.md` and all 8 `phase-*.md` files.
- Decision deltas checked: 4.
- Reconciled stale references: 4.
- Unresolved contradictions: 0.

Plan is validated for implementation. User explicitly said not to run `/ck:cook` in this session.

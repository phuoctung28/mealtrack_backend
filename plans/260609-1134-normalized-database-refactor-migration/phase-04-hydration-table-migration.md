---
phase: 4
title: "Hydration table migration"
status: completed
priority: P1
effort: "1-2 weeks"
dependencies: [1, 2]
---

# Phase 4: Hydration table migration

## Context Links

- Commands: `src/app/handlers/command_handlers/log_hydration_command_handler.py`, `src/app/handlers/command_handlers/log_caloric_drink_command_handler.py`
- Queries: `src/app/handlers/query_handlers/get_daily_hydration_query_handler.py`, `src/app/handlers/query_handlers/get_weekly_hydration_query_handler.py`
- Repository: `src/infra/repositories/meal_repository_async.py`

## Overview

Move hydration from overloaded `meal` rows into a dedicated normalized table while keeping hydration APIs and daily macro behavior compatible.

## Key Insights

- Hydration currently writes `Meal` with `meal_type="hydration"`, `source="hydration"`, placeholder image, and `quantity` as credited ml.
- Previous `hydration_logs` table existed and was dropped. This phase reintroduces the concept with a better compatibility rollout.

## Requirements

- Functional: hydration endpoints return the same response shape.
- Functional: daily/weekly hydration summaries read normalized rows first, legacy meal rows second.
- Non-functional: no double counting during dual-write.

## Architecture

Create `hydration_entries` as source of truth. Keep caloric drinks linked to nutrition semantics explicitly:

- `id`
- `user_id` FK
- `drink_id`
- `drink_name_snapshot`
- `emoji_snapshot`
- `volume_ml`
- `credited_ml`
- `protein_g`
- `carbs_g`
- `fat_g`
- `fiber_g`
- `sugar_g`
- `logged_at`
- `source`
- optional `legacy_meal_id` unique nullable for migration traceability.

Do not store both `kcal` and `calories`. Backend derives calories from stored macro fields and exposes `kcal` and `calories` as response aliases for API compatibility.

During rollout, write hydration entry and optionally legacy meal row behind a feature/config guard until reads are stable.

## Related Code Files

| Action | File |
|---|---|
| Create | `src/infra/database/models/hydration_entry.py` |
| Create | `src/domain/model/hydration/hydration_entry.py` |
| Create | `src/infra/repositories/hydration_repository_async.py` |
| Modify | `src/infra/database/uow_async.py` |
| Modify | `src/app/handlers/command_handlers/log_hydration_command_handler.py` |
| Modify | `src/app/handlers/command_handlers/log_caloric_drink_command_handler.py` |
| Modify | `src/app/handlers/command_handlers/delete_hydration_entry_command_handler.py` |
| Modify | `src/app/handlers/query_handlers/get_daily_hydration_query_handler.py` |
| Modify | `src/app/handlers/query_handlers/get_weekly_hydration_query_handler.py` |
| Modify | `src/app/handlers/query_handlers/get_daily_macros_query_handler.py` |
| Create | `migrations/versions/YYYYMMDDHHMMSS_add_hydration_entries.py` |
| Modify/Add | `tests/unit/handlers/command_handlers/test_log_caloric_drink_command_handler.py` |
| Modify/Add | `tests/unit/handlers/query_handlers/test_daily_hydration_query_handler.py` |

## Implementation Steps

1. Tests before: assert current hydration API response, calories, streak, delete behavior, and daily macros inclusion/exclusion.
2. Add `hydration_entries` table/model with FK/index `(user_id, logged_at)`, macro fields, and optional unique `legacy_meal_id`.
3. Backfill from `meal` where `meal_type='hydration' OR source='hydration'`, preserving IDs via `legacy_meal_id`.
4. Add repository methods:
   - create/delete by entry id or legacy meal id;
   - sum by day/date range;
   - list by day.
5. Update command handlers to write normalized rows with macro fields. Keep legacy dual-write only while read fallback is active.
6. Update queries to read normalized entries first and derive calories from macros; if none found for a date, fallback to legacy `meal` hydration rows.
7. Update cache invalidation to keep existing keys stable.
8. Add a guard against double counting when both normalized and legacy rows exist.

## Test Scenario Matrix

| Scenario | Test |
|---|---|
| Legacy hydration meal backfills to entry | migration test |
| Dual-written date counts once | query unit/integration |
| Daily hydration response unchanged | route/query test |
| Weekly hydration chart unchanged | query test |
| Delete hydration handles normalized + legacy ids | command test |
| Daily macros keep backend-derived calories | daily macros test |
| Hydration table does not store duplicate calorie fields | model/migration test |

## Success Criteria

- [x] New hydration writes create `hydration_entries`.
- [x] Legacy hydration rows remain readable during rollout.
- [x] No placeholder `MealImage` needed for normalized hydration entries.
- [x] No double count in hydration, daily activities, or macros.
- [x] `kcal` and `calories` remain response aliases, not duplicated stored columns.

## Risk Assessment

High product risk because hydration appears in multiple daily summary paths. Mitigation: preserve API response, add double-count tests, and keep fallback until production data is verified.

## Security Considerations

Hydration entries are private user health logs; FK cascade/anonymization must match account-deletion policy.

## Next Steps

Once hydration no longer depends on `meal`, normalize saved suggestion and recipe payloads.

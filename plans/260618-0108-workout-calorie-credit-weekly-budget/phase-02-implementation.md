---
phase: 2
title: Implementation
status: completed
priority: P1
effort: 1.5h
dependencies:
  - 1
---

# Phase 2: Implementation

## Overview

Implement movement-aware weekly calorie consumption and remove stale duplication from the weekly budget query handler.

## Requirements

- Functional: weekly calorie consumption is `meal-derived calories - included movement kcal`.
- Functional: consumed protein/carbs/fat remain based on food macros only.
- Functional: BMR floor, deficit/surplus caps, remaining-days semantics, cheat-day handling, and logging prompt behavior stay intact.
- Non-functional: keep the domain service dependency-free and use existing UoW repositories.

## Architecture

`WeeklyBudgetService` remains the source of truth. It calculates food macros from meals and subtracts movement kcal for calories only when the UoW exposes `movement_entries`. The weekly query handler delegates to `WeeklyBudgetService.get_effective_adjusted_daily_async` instead of maintaining a second adjustment implementation.

## Related Code Files

- Modify: `src/domain/services/weekly_budget_service.py`
- Modify: `src/app/handlers/query_handlers/get_weekly_budget_query_handler.py`
- Read: `src/infra/repositories/movement_repository_async.py`
- Read: `src/app/handlers/query_handlers/get_daily_macros_query_handler.py`

## Implementation Steps

1. Add a local-date to UTC range helper in `WeeklyBudgetService`.
2. Add async movement kcal subtraction to `calculate_weekly_consumed_async`.
3. Keep sync `calculate_weekly_consumed` behavior unchanged unless movement support is naturally available without async IO.
4. Update `get_effective_adjusted_daily_async` cap and redistribution math to use net consumed calories returned by the consumed helper.
5. Remove `GetWeeklyBudgetQueryHandler._get_effective_adjusted_daily_async` and call the domain service directly.
6. Keep weekly response shape unchanged; `consumed_calories` becomes net to match daily/bulk semantics.

## Success Criteria

- [x] Weekly service uses `sum_included_kcal_for_range` for the exact local date range being summed.
- [x] Macro consumed values do not subtract movement.
- [x] Weekly handler has no duplicate redistribution implementation.
- [x] No new schema, migration, or response field is introduced.

## Risk Assessment

Risk: negative weekly consumed calories if workouts exceed food. Mitigation: allow it as valid net balance, matching daily nutrition behavior.

Risk: response consumers expected weekly `consumed_calories` as food-only. Mitigation: daily/bulk already expose calories as net; movement docs already define calorie balance this way.

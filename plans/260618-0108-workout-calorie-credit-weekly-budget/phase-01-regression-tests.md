---
phase: 1
title: Regression Tests
status: completed
priority: P1
effort: 45m
dependencies: []
---

# Phase 1: Regression Tests

## Overview

Add focused tests that prove weekly budget uses movement-adjusted calories while keeping macro grams food-only.

## Requirements

- Functional: `2300 food - 200 workout` behaves as `2100` consumed for weekly calorie redistribution.
- Functional: `include_in_balance = false` movement is ignored.
- Functional: movement logged after the target date does not change the selected day's adjustment.
- Non-functional: no DB schema or public API shape changes.

## Architecture

Tests should target `WeeklyBudgetService.get_effective_adjusted_daily_async` and the weekly query handler path. Use existing fake repositories and async mocks; no database required.

## Related Code Files

- Modify: `tests/unit/domain/services/test_weekly_budget_async.py`
- Modify: `tests/unit/handlers/query_handlers/test_cached_query_handlers.py`
- Read: `tests/unit/handlers/query_handlers/test_movement_balance_integration.py`
- Read: `src/domain/services/weekly_budget_service.py`

## Implementation Steps

1. Add an async fake movement repository with `sum_included_kcal_for_range`.
2. Add a weekly service regression for Monday food 2300 kcal, Monday movement 200 kcal, Tuesday target date.
3. Add ignored-movement and future-movement coverage.
4. Add handler-level coverage proving response `consumed_calories`, `remaining_calories`, and preview math use the service net totals.
5. Run the focused tests once to confirm they fail before implementation where practical.

## Success Criteria

- [x] Service test expects adjusted calories near the net-calorie weekly result.
- [x] Excluded/future movement tests prove correct range/filter handling.
- [x] Handler test proves weekly endpoint consumes the service result and does not use stale inline meal-only math.

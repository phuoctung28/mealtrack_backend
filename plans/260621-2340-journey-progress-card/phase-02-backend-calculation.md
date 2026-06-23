---
phase: 2
title: Backend Calculation
status: completed
priority: P1
effort: 5h
dependencies:
  - 1
---

# Phase 2: Backend Calculation

## Overview

Implement the canonical calculation for action-based journey progress. The strict period filter is the core feature: count only `period_start <= action_time < period_end`.

## Requirements

- Functional: existing users use the later of `goal_started_at` and the stable 2026-06-21 feature start in their timezone, so old logs are excluded.
- Functional: new onboarding with `target_weight_kg` sets `goal_start_weight_kg` and `goal_started_at`.
- Functional: scoring mirrors current mobile weights: calories 30%, protein 15%, meal count 20%, hydration 15%, movement 20%.
- Functional: today's progress is capped at `100 / timelineDays`; logged actions get the visible floor.
- Non-functional: use indexed range reads and avoid per-day query loops.

## Architecture

`GetJourneyProgressQueryHandler` resolves timezone/profile, derives the active period, gathers meals/hydration/movement/weight logs within the strict UTC window, and returns a precomputed snapshot. Existing repositories should get focused range helpers where needed.

## Related Code Files

- Create: `src/app/handlers/query_handlers/get_journey_progress_query_handler.py`
- Modify: `src/app/handlers/query_handlers/__init__.py`
- Modify: `src/infra/repositories/meal_repository_async.py`
- Modify: `src/infra/repositories/hydration_repository_async.py`
- Modify: `src/infra/repositories/movement_repository_async.py`
- Modify: `src/infra/repositories/weight_repository_async.py`
- Modify: `src/app/handlers/command_handlers/save_user_onboarding_command_handler.py`
- Add/modify tests under `tests/unit/handlers/query_handlers/` and `tests/unit/handlers/command_handlers/`

## Implementation Steps

1. Add small repository helpers for action summary ranges if existing methods are insufficient.
2. Derive timeline days from fitness goal and weight delta using existing mobile constants.
3. Compute daily scores for days from period start through `as_of`, capped by daily budget and total 100%.
4. Select latest action from included meal, hydration, movement, and weight logs.
5. Set onboarding goal baseline fields only when a target weight exists and baseline is absent.
6. Add unit tests for strict lower/upper boundaries, no historical backfill, scoring, and onboarding baseline.

## Success Criteria

- [ ] Logs before `period_start` do not affect percent or latest action.
- [ ] Logs exactly at `period_start` count.
- [ ] Logs at `period_end` do not count.
- [ ] Existing users without a start date receive a current-period start.
- [ ] New onboarding stores start weight and start timestamp when target weight exists.

## Risk Assessment

Risk: timezone errors shift actions across period boundary. Mitigation: convert local period bounds to UTC once and pass UTC windows to repositories.

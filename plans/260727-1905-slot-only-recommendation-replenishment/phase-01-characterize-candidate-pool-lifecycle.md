---
phase: 1
title: "Characterize Candidate Pool Lifecycle"
status: in-progress
priority: P1
effort: "1-1.5d"
dependencies: []
---

# Phase 1: Characterize Candidate Pool Lifecycle

## Overview

Add tests that prove the present cycle, then introduce durable candidate lifecycle fields so unseen, seen, active, and retired candidates are distinguishable per slot.

## Related Code Files

- Modify: `src/infra/database/models/meal_recommendation/meal_recommendation_plan.py`
- Create: `migrations/versions/<timestamp>_add_meal_recommendation_candidate_pool_lifecycle.py`
- Modify: `src/infra/repositories/meal_recommendation_plan_repository_async.py`
- Modify: `src/app/handlers/command_handlers/meal_recommendation/create_three_day_meal_recommendation_command_handler.py`
- Modify: `tests/unit/infra/repositories/test_meal_recommendation_plan_repository_async.py`
- Create: `tests/integration/postgres/test_meal_recommendation_slot_concurrency.py`

## Requirements

- A new plan records the selected candidate as seen and its five alternatives as unseen.
- Retired candidates remain auditable but are excluded from slot detail and future automatic selection.
- The currently selected candidate remains in the active pool during replenishment; five new alternatives form its next active pool.
- Forward-only migration only; do not edit deployed migration history.

## Tests Before

1. Characterize today’s automatic rank-0/rank-1 cycle.
2. Prove a candidate selected once is never returned by automatic swap again.
3. Prove retired candidates are absent from active slot detail while historical operations remain valid.
4. Run migration upgrade against PostgreSQL integration database and assert safe legacy defaults.

## Implementation Steps

1. Add minimal lifecycle persistence (`seen_at` and an active-pool discriminator) to recommendation candidate rows; name columns from their invariant, not this plan.
2. Backfill existing selected rows as seen. Keep old inactive candidates available only until normal lifecycle handling safely retires them; document exact compatibility behavior in migration comments.
3. Restrict active slot loaders/serializers to the current candidate pool while retaining owner-anchor authorization.
4. Mark the initially selected candidate seen during plan persistence.

## Success Criteria

- [x] Candidate lifecycle fields and additive migration preserve candidate history.
- [ ] An active replenished slot exposes exactly one selected candidate plus five active alternatives in PostgreSQL integration coverage.
- [ ] Migration downgrade is tested against PostgreSQL.

## Risks

Legacy active slots lack prior selection history. Treat their current selected meal as seen at migration time; do not invent historical data.

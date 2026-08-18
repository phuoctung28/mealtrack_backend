---
title: "Catalog meal log insight and relog"
description: "Warm meal value insights when a catalog recommendation is logged, and allow logging the same catalog recipe again without replacing the slot's original logged meal."
status: in-progress
priority: P1
branch: "delivery"
tags: [feature, backend, catalog, meal-recommendations, insights]
created: "2026-08-18"
source: skill
---

# Catalog meal log insight and relog

The local plan path was not present in git. This in-repo plan records the
workstreams implemented from that title and from the current catalog log gap:
`LogRecommendedMealCommandHandler` persists a READY meal but never schedules
value insights, unlike scan, parse-text, and manual save.

## Worktrees

Both worktrees live inside this repo (gitignored `.worktrees/`):

- `.worktrees/catalog-meal-log-insight` → `feature/catalog-meal-log-insight-6b97`
- `.worktrees/catalog-meal-relog` → `feature/catalog-meal-relog-6b97`

## Phases

| Phase | Name | Status | Branch |
|-------|------|--------|--------|
| 1 | Catalog log insight warmup | In progress | `feature/catalog-meal-log-insight-6b97` |
| 2 | Catalog meal relog | In progress | `feature/catalog-meal-relog-6b97` |

## Acceptance

### Phase 1 — insight

- First-time `POST .../slots/{slot_id}/log` materialization schedules
  profile-aware meal value insights with `source=catalog_log`.
- Scheduling is best-effort and cannot fail the log.
- Idempotent log replay does not spawn a second insight task.
- Calories remain backend-derived; clients still read insights from meal detail
  / `GET /v1/meals/{meal_id}/value-insights`.

### Phase 2 — relog

- `POST .../slots/{slot_id}/relog` materializes a **new** meal from the current
  selected catalog recipe.
- Relog requires the slot to already be logged; skipped/unlogged slots stay
  terminal/not-logged errors.
- Slot `logged_meal_id` is unchanged (first log remains the plan pointer).
- Relog is request-id idempotent via `operation_type='relog'`.
- The new meal is dated to the user's today in the plan timezone.
- Relog also warms value insights for the new meal.

## Out of scope

- Changing first-log slot semantics or allowing duplicate slot `logged_meal_id`.
- Mobile client work.
- Recalculating calories on the client.

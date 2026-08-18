---
phase: 2
title: "Catalog meal relog"
status: in-progress
priority: P1
---

# Phase 2: Catalog meal relog

Add `POST /v1/meal-recommendations/{plan_id}/slots/{slot_id}/relog`.

- Requires the slot to already be logged.
- Materializes a new meal dated to the user's today.
- Leaves `logged_meal_id` pointing at the original log.
- Request-id idempotent via `operation_type='relog'`.
- Warms meal value insights for the new meal.

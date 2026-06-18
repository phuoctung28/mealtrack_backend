# Movement Feature — Backend Release Readiness

**Date:** 2026-05-31
**Audience:** Backend team
**Scope:** Everything to confirm/address before releasing the Movement (activity logging) feature.
**Reviewed against mobile contract:** `nutree_ai` movement feature (log/edit/delete + dashboard calorie integration).

This document is the result of a cross-repo review of the backend movement implementation against what the mobile app sends and expects. It separates **verified-correct** (no action) from **must address**, **should address**, and **optional**, and ends with a **locked contract** the backend must not break without a coordinated mobile release.

---

## 0. TL;DR

The backend implementation is **functionally complete and largely correct**. There are **no hard code blockers** — endpoints, schemas, net-calorie math, cache invalidation, indexes, and timezone handling all check out. The pre-release work is mostly **operational** (run the migration) and **decisions** (kcal trust model, catalog ownership, dead-code cleanup).

---

## 1. Verified correct — no action needed

These were checked against the mobile contract and are correct:

| Area | Finding |
|------|---------|
| **Endpoints** | `POST /v1/movement/log`, `GET /v1/movement/daily`, `PATCH /v1/movement/{id}`, `DELETE /v1/movement/{id}`, `GET /v1/movement/catalog` all present and match mobile calls. |
| **Activities feed** | `GET /v1/activities/daily` `_build_movement_activity` emits exactly the fields mobile parses: `id, type="movement", timestamp, title, activity_id, intensity, duration_min, kcal_burned, source, include_in_balance`. |
| **`/movement/daily` shape** | Returns `{date, goal_kcal, entries[]}`; entries use `_movement_response`. Matches mobile `MovementDailyResponse`. |
| **Net-calorie math** | `get_daily_macros_query_handler` returns `total_calories = food_calories − movement_kcal_burned` (net), plus `food_calories` and `movement_kcal_burned`. Burn correctly frees up the calorie budget. |
| **Bulk consistency** | `get_nutrition_bulk_query_handler` applies the same `net = food − movement` per day → weekly budget stays consistent with daily. |
| **Weekly budget consistency** | `WeeklyBudgetService.get_effective_adjusted_daily_async` applies the same net calorie balance (`food − included movement`) to adjusted daily targets, remaining calories, weekly context, and tomorrow preview. Macro gram totals stay food-only. |
| **TDEE baseline boundary** | Planned training volume does not inflate baseline TDEE. Logged movement is the only workout calorie credit, which avoids double-counting exercise. |
| **`include_in_balance` filter** | `sum_included_kcal_for_range` filters `include_in_balance IS TRUE`. The feed (`find_by_user_and_logged_range`) returns all entries (so excluded ones still render but don't affect calories). Correct. |
| **Cache invalidation** | Log **and** update **and** delete all call `_flush_movement_caches` → invalidates `daily_macros`, `weekly_budget`, and `activities:{date}:*`. No stale dashboard after mutations. |
| **DB indexes** | Migration creates composite `idx_movement_entries_user_logged_at (user_id, logged_at)` — matches the daily range query. FK to `users` with `ON DELETE CASCADE`. |
| **Timezone** | Handlers resolve user tz via `X-Timezone` header → stored user tz → UTC fallback. Day windows computed in user-local time. Mobile injects `X-Timezone` on every request. Week-start (`get_user_monday`, Monday-based) matches the flush's `weekday()` computation. |
| **Intensity enum** | Backend `{light, moderate, hard}`. Mobile's 3-option control sends exactly these. |
| **Edit protection** | Update handler rejects editing `source="apple_health"` entries with `403 APPLE_HEALTH_NOT_EDITABLE`. |
| **Future-date guard** | Log rejects `target_date > today + 1 day`. |

---

## 2. MUST address before release

### 2.1 Run the migration in staging + production
`migrations/versions/20260531000001_add_movement_entries_table.py` creates `movement_entries`. Confirm it is applied in the deploy pipeline for both environments before the mobile build ships. Verify `down_revision` chains cleanly from the current head.

### 2.2 `kcal_burned` trust model — **DECIDED: client-trust with sanity bounds**
The backend stores the client-supplied `kcal_burned` verbatim. Decision: **option (a) — keep client-trust**. Mobile is the source of truth for MET computation.

Sanity bounds added (both `log` and `update`):
- `kcal_burned > 5000` → `400 INVALID_KCAL`
- `kcal_burned > duration_min × 25` → `400 INVALID_KCAL` (25 kcal/min ≈ elite cyclist ceiling)

### 2.3 Treat the catalog IDs as a frozen contract
`log_movement_command_handler._validate_log_movement` rejects any `activity_id` not in `movement_catalog_service` with `400 INVALID_ACTIVITY`. The mobile app now sends `activity_id` for presets (and `null` for custom). **Renaming or removing any catalog `id` is a breaking change** that will:
1. reject new logs for that activity (`400`), and
2. break icon resolution for historical entries on mobile.

See §5 for the locked ID list. Any change must ship with a coordinated mobile release + a data migration for stored `activity_id` values.

---

## 3. SHOULD address

### 3.1 Remove dead `WorkoutActivityResponse` schema
`src/api/schemas/response/activity_responses.py` defines `WorkoutActivityResponse` with `type="workout"`. The feed never uses it — `_build_movement_activity` returns a dict with `type="movement"`. Dead/misleading; remove or align the name to `movement` to avoid future confusion.

### 3.2 Catalog ownership — **DECIDED: `/movement/catalog` is source of truth**
Decision: **option (a)**. Mobile must fetch `GET /v1/movement/catalog` on app launch and cache it locally (static list as offline fallback). Backend `movement_catalog_service` is the single source of truth for IDs, names, MET values, and `apple_health_type` mapping. Any catalog edit ships backend-only — no mobile release needed.

### 3.3 Verify `/movement/daily` vs `/activities/daily` day-window parity
The movement screen reads `/movement/daily`; the dashboard reads `/activities/daily`. Both compute the day window in user-local tz, so they should agree — but confirm with a boundary test (entry logged at 23:30 local, queried the next morning) that the same entry appears in both, to avoid the two screens disagreeing at midnight.

---

## 4. OPTIONAL / future

- **`goal_kcal` is hardcoded `300.0`** in `/movement/daily`. The mobile **no longer displays a movement goal** (removed from the UI), so this is currently moot. If a per-user movement goal is ever reintroduced, wire it to the user profile.
- **Apple Health import**: `MovementSource.APPLE_HEALTH` and edit-protection exist, but there is **no import endpoint**. The feed and daily-macros already handle `source="apple_health"` entries correctly if they appear. Document Apple Health as not-yet-released so QA doesn't expect it.
- **`very_hard` intensity**: mobile defines MET values for a 4th level but never sends it (3-option control). Backend enum has only 3. If a 4th level is ever exposed, add it to `MovementIntensity` **and** every catalog entry's `met` map first, or logging will `400`.

---

## 5. Locked contract (do not break without coordinated mobile release)

### Catalog IDs (must match mobile `ActivityCatalog`)
```
walking, running, cycling, gym_strength, cardio_hiit,
yoga_stretching, swimming, badminton, football, volleyball
```
Custom activities send `activity_id = null` (no `custom` id on the backend — sending `"custom"` would be rejected).

### Enums
- `intensity` ∈ `{light, moderate, hard}`
- `source` ∈ `{manual, apple_health}`

### Request fields mobile sends
- **`POST /movement/log`**: `activity_name` (required), `activity_id` (preset id or omitted/null for custom), `duration_min`, `kcal_burned`, `intensity`, `include_in_balance`, `target_date` (optional `YYYY-MM-DD`), `X-Timezone` header.
- **`PATCH /movement/{id}`**: `duration_min`, `kcal_burned`, `intensity`, `include_in_balance`. (No `activity_id` / `activity_name` — session params only.)

### Response fields mobile parses
- Feed entry & `_movement_response`: `id, activity_name, duration_min, kcal_burned, intensity, source, include_in_balance, logged_at` (+ `activity_id`, `type`, `timestamp` in the feed). Extra fields are ignored safely.
- `daily-macros`: mobile reads `target_calories`, `target_macros`, and the consumed/macros values. `total_calories` is net (food − burn); mobile recomputes consumed locally and does **not** double-subtract.
- `weekly-budget`: `consumed_calories`, `remaining_calories`, `adjusted_daily_calories`, and preview fields use net calories. `consumed_protein`, `consumed_carbs`, and `consumed_fat` remain food macro grams. Baseline TDEE excludes planned workouts, so logged movement is not a second credit for exercise already included in targets.

---

## 6. Pre-release checklist

- [ ] Migration `20260531000001` applied in staging and production.
- [x] `kcal_burned` trust model decided — client-trust, bounds: `> 5000` or `> duration_min × 25` → 400 (§2.2).
- [x] Catalog IDs confirmed frozen; locked list in §5 (§2.3).
- [x] `WorkoutActivityResponse` removed from `activity_responses.py` (§3.1).
- [x] Catalog ownership: `/movement/catalog` is source of truth; mobile must fetch + cache (§3.2).
- [x] Day-boundary parity: UTC window test added — HCM 23:30 in May 29 window, 00:30 outside (§3.3).
- [x] Weekly budget movement credit: adjusted daily targets use `food − included movement`, matching daily and bulk nutrition.
- [x] TDEE baseline boundary: planned training does not increase baseline TDEE; workout credit comes from logged movement.
- [ ] Load/peek: daily range query uses `idx_movement_entries_user_logged_at` (confirm via `EXPLAIN`).
- [ ] Apple Health documented as not-yet-released (§4).

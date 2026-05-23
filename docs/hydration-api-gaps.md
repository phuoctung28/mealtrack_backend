# Hydration API — Backend Gaps & Required Changes

**Created:** 2026-05-23  
**Scope:** Changes the backend team must make before mobile can integrate `api-hydration.md`  
**Mobile counterpart:** `nutree_ai/docs/hydration-integration-plan.md`

---

## 1. Missing Endpoints

### 1.1 `GET /v1/hydration/weekly`

Mobile currently stores 7-day history in `SharedPreferences`. This is lost on reinstall and won't sync across devices.

**Required response:**

```json
{
  "week_start": "2026-05-19",
  "days": [
    { "date": "2026-05-19", "consumed_ml": 1800 },
    { "date": "2026-05-20", "consumed_ml": 2100 },
    { "date": "2026-05-21", "consumed_ml": 950 },
    { "date": "2026-05-22", "consumed_ml": 2000 },
    { "date": "2026-05-23", "consumed_ml": 750 },
    { "date": "2026-05-24", "consumed_ml": 0 },
    { "date": "2026-05-25", "consumed_ml": 0 }
  ],
  "goal_ml": 2000
}
```

**Query params:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `start_date` | `YYYY-MM-DD` | No | Monday of the desired week. Defaults to current week's Monday in user's timezone. |

**Headers:** `X-Timezone` (same as other endpoints)

---

### 1.2 `GET /v1/hydration/streak`

Mobile currently computes streak locally in SharedPreferences. Breaks on reinstall.

**Required response:**

```json
{
  "current_streak": 5,
  "last_logged_date": "2026-05-23"
}
```

A streak day = any day where `consumed_ml >= goal_ml`.  
`current_streak` resets to `0` if `last_logged_date` is before yesterday.

**Alternative (preferred):** Add `streak` to the `GET /v1/hydration/daily` response to avoid an extra round trip:

```json
{
  "date": "2026-05-23",
  "consumed_ml": 1250,
  "goal_ml": 2000,
  "percentage": 62.5,
  "streak": 5,
  "entries": [...]
}
```

---

## 2. API Spec Inconsistencies to Fix

### 2.1 `entry_id` vs `id` key inconsistency

`POST /v1/hydration/log` response uses `entry_id`:
```json
{ "entry_id": "3fa85f64-...", ... }
```

`GET /v1/hydration/daily` entries use `id`:
```json
{ "id": "3fa85f64-...", ... }
```

**Fix:** Standardise on `id` across all responses. `entry_id` in the POST response is inconsistent with every other entity in the API.

---

### 2.2 `POST /v1/hydration/log/drink` response is too thin

Current response only returns `entry_id` and `meal_id`:
```json
{ "entry_id": "...", "meal_id": "..." }
```

Mobile needs the hydration entry fields to update the local state optimistically. **Add the full `HydrationEntry` to the response**, same shape as `POST /v1/hydration/log`:

```json
{
  "id": "...",
  "meal_id": "...",
  "drink_id": "milk-tea",
  "drink_name": "Milk tea",
  "emoji": "🧋",
  "volume_ml": 500,
  "credited_ml": 350,
  "kcal": 380.0,
  "source": "caloric_drink",
  "logged_at": "2026-05-23T08:00:00Z"
}
```

---

### 2.3 Fat calculation can produce negative values

From the spec:
> `fat = (kcal - sugar×4) / 9`

For a drink where `sugar_per_100ml × 4 > kcal_per_100ml` (e.g., future drinks), fat would be negative. Mobile will clamp to 0 as a workaround, but **the formula should be clarified in the spec** — either guarantee `kcal >= sugar×4` in the catalog, or change to `fat = max(0, (kcal - sugar×4) / 9)`.

---

### 2.4 `coke-zero` category issue

API catalog has `coke-zero` as `category: "caloric"` even though `kcal_per_100ml = 0`. This is intentional (it creates a meal entry). **Document this explicitly** in `api-hydration.md` so both backend and mobile handle it the same way — category, not kcal, determines the log endpoint to use.

---

## 3. Minor Clarifications Needed

| # | Item | Location |
|---|------|----------|
| 3.1 | `goal_ml` source — is it per-user configurable, or always 2000 for now? Document the future endpoint for setting it. | `GET /daily` response |
| 3.2 | `DELETE /v1/hydration/{entry_id}` returns bare `true` — standardise to `{ "success": true }` for consistency with other delete endpoints. | `DELETE` response |
| 3.3 | Is `target_date` validated server-side against future dates? Max days in past? Document the 422 case. | `POST /log` |
| 3.4 | `sub` is `string \| null` in the spec but `string` in all catalog examples. Confirm nullability for mobile parsing. | `Drink` model |

---

## 4. Priority Order

| Priority | Task | Blocking mobile? |
|----------|------|-----------------|
| P0 | Fix `entry_id` → `id` in POST response | Yes — mobile can't parse log response |
| P0 | Enrich `POST /log/drink` response (see 2.2) | Yes — caloric log flow broken |
| P1 | Add `GET /v1/hydration/weekly` | Yes — weekly chart can't work without it |
| P1 | Add `GET /v1/hydration/streak` or add to `/daily` | Yes — streak can't be server-persisted |
| P2 | Clarify fat formula (2.3) | No — mobile workaround exists |
| P2 | Document coke-zero category intent (2.4) | No — mobile uses category field |
| P3 | Minor clarifications (3.x) | No |

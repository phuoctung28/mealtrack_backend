# D1-D3 Onboarding Retention Campaign — Mobile Payload Contract

_Generated: 2026-06-21 | Branch: feature/d1-d3-retention-campaign_

---

## 1. Seven Notification Types and Local Trigger Rules

| # | `type` value | Campaign day | Local time | Backend fires when |
|---|---|---|---|---|
| 1 | `d1_night_anchor` | D1 | 21:00 user local | Stale check: only if `now_utc < 21:00 local`. Skipped if cron runs after 21:00. |
| 2 | `d2_morning_steps_sync` | D2 | 08:30 user local | No stale check — fires on first cron after 08:30 local if not yet sent |
| 3 | `d2_lunch_refuel` | D2 | 11:45 user local | No stale check |
| 4 | `d2_hydration_slump` | D2 | 15:00 user local | No stale check |
| 5 | `d2_daily_summary` | D2 | 20:00 user local | No stale check; suppresses normal `daily_summary` for campaign D2 (see §6) |
| 6 | `d3_churn_preemption` | D3 | 09:00 user local | No stale check |
| 7 | `d3_premium_asset_lock` | D3 | `trial_end - 6h` UTC | Computed from `subscriptions.expires_at` or fallback (see §8) |

All rows are inserted by the cron scheduler phase via `ON CONFLICT DO NOTHING` on `(user_id, notification_type, scheduled_date)` — idempotent across runs.

---

## 2. FCM Data Payload Contract

All campaign notifications arrive as FCM **data-only messages** (no APNS `notification` object). Mobile must render the UI from `data` keys.

```
data {
  "type":               string   // notification type string (see §2.1)
  "notification_ids":   string   // comma-separated DB notification UUIDs
  "notification_count": string   // count of IDs as string ("1")
  "campaign":           string   // always "onboarding_d1_d3"
  "campaign_day":       string   // "1", "2", or "3"
  "campaign_step":      string   // step slug (see §3)
  "deeplink":           string   // nutree:// URI (see §3)
  "display_mode":       string   // rendering hint (see §3)
}
```

### 2.1 `type` value note

The `type` key carries the **notification type as-is for campaign types** (e.g. `d1_night_anchor`, `d2_morning_steps_sync`, etc.). The only aliasing that occurs is for non-campaign `trial_expiry_2d` / `trial_expiry_1d` → normalized to `trial_expiry` in FCM, but all seven campaign types pass through unchanged.

### 2.2 Non-campaign notifications (not affected by this feature)

Regular notifications (`meal_reminder_*`, `daily_summary`, `trial_expiry`, `hydration_reminder_*`) do **not** receive `campaign`, `campaign_day`, `campaign_step`, `deeplink`, or `display_mode` keys.

---

## 3. Per-Type Deeplink and Display Mode Table

| `type` | `campaign_step` | `deeplink` | `display_mode` |
|---|---|---|---|
| `d1_night_anchor` | `night_anchor` | `nutree://retention/mobility-intent` | `mobility_modal` |
| `d2_morning_steps_sync` | `morning_steps_sync` | `nutree://today-log/morning` | `steps_sync` |
| `d2_lunch_refuel` | `lunch_refuel` | `nutree://today-log` | `fast_log` |
| `d2_hydration_slump` | `hydration_slump` | `nutree://hydration` | `hydration_charge` |
| `d2_daily_summary` | `daily_summary` | `nutree://daily-summary` | `summary` |
| `d3_churn_preemption` | `churn_preemption` | `nutree://progress-warning` | `badge_prompt` |
| `d3_premium_asset_lock` | `premium_asset_lock` | `nutree://premium/asset-lock` | `premium_asset_lock` |

---

## 4. Endpoint Contracts

### PUT /v1/retention/onboarding/mobility-intent

Records user's commute choice from the D1 Night Anchor modal. Upserts `onboarding_retention_states` and starts the campaign clock.

**Auth**: Firebase JWT required (`Authorization: Bearer <token>`).

**Request body:**
```json
{
  "tomorrow_mobility_type": "public_transit" | "motorbike" | "car_taxi"
}
```

**Response 200:**
```json
{ "success": true }
```

**Error 400:** returned only if user's `onboarding_completed = false` in DB. A missing DB row (stub/new user) is treated permissively and proceeds.

**Side effect:** sets `campaign_started_at = now()` and `campaign_timezone = user.timezone` on first call. Subsequent calls update `tomorrow_mobility_type` only (idempotent upsert).

---

### GET /v1/retention/onboarding/asset-summary

Returns campaign asset counts and trial window for D3 UI.

**Auth**: Firebase JWT required.

**Response 200:**
```json
{
  "meal_scan_count":        int,    // meals scanned via camera since campaign_started_at
  "hydration_entry_count":  int,    // total hydration log entries since campaign_started_at
  "hydration_win_count":    int,    // distinct days with at least one hydration entry
  "movement_entry_count":   int,    // total movement entries since campaign_started_at
  "active_day_count":       int,    // distinct days with any log (meal, hydration, or movement)
  "trial_end_at":           string | null,  // ISO-8601 UTC datetime or null
  "lock_at":                string | null   // ISO-8601 UTC datetime; = trial_end_at - 6h
}
```

If no campaign state exists yet (user never called mobility-intent), all counts are `0` and timestamps are `null`. Mobile must handle this gracefully.

---

## 5. D1 Stale Rule

If the cron scheduler runs **after 21:00 in the user's local timezone on D1**, the `d1_night_anchor` notification is **not inserted** and will not fire at all for that user's Day 1.

This means: if a user completes onboarding after 21:00 local (and triggers `PUT mobility-intent` after that time), the `d1_night_anchor` push will be skipped. Mobile must not depend on D1 Night Anchor always arriving — design the D1 modal flow defensively.

---

## 6. D2 Summary Duplicate Suppression Rule

When the cron scheduler inserts a `d2_daily_summary` row for campaign D2, it **deletes any `pending` `daily_summary` rows** for the same user on the same local date from the `notifications` table.

- Only `status = 'pending'` rows are deleted. Already-sent or failed rows are preserved.
- Affects D2 only — D1 and D3 do not suppress normal notifications.
- Mobile receives exactly one summary push on D2 (the campaign version with `display_mode=summary`).

---

## 7. Health Sync Rule (D2 Morning Steps)

Backend sends `d2_morning_steps_sync` with **static copy** ("Morning, sync your steps from yesterday") regardless of whether movement data has arrived.

Mobile is expected to:
1. Sync HealthKit (iOS) / Health Connect (Android) steps/movement to the backend **before 08:30 local on D2**.
2. The backend uses whatever `movement_entries` exist at send time for any dynamic rendering (currently static copy — no server-side personalization of step count in the body).
3. If no movement data has arrived by 08:30, the same generic copy is sent — no suppression.

Backend does not delay or retry this push waiting for health data.

---

## 8. Trial Timing Rule

The `d3_premium_asset_lock` push time is calculated as:

```
asset_lock_utc = trial_end_at - 6 hours
```

Where `trial_end_at` is resolved in priority order:
1. **Primary**: `subscriptions.expires_at` WHERE `status = 'active'` for the user (RevenueCat source of truth).
2. **Fallback**: `campaign_started_at + 72 hours` (used when no active subscription row exists).

The same logic is mirrored in `GET /v1/retention/onboarding/asset-summary` — the `lock_at` field in the response equals `trial_end_at - 6h`.

Mobile must use backend-provided `trial_end_at` and `lock_at` values from the asset-summary endpoint — do not recompute on device.

---

## 9. Copy Safety Rule

All D3 copy (churn preemption and premium asset lock) uses **"locked" and "unavailable" language only**. Examples:

- "Your trial features become unavailable soon"
- "Tính năng dùng thử sắp bị khóa rồi"
- "Your 3-day progress is at risk of being lost"

No copy claims data is **deleted**. Mobile UI must follow the same rule — show lock/unavailable states, never deletion confirmations.

---

## 10. Mobile-Owned Behavior (Backend Does Not Implement)

| Concern | Mobile responsibility |
|---|---|
| HealthKit / Health Connect data sync | Mobile initiates sync before D2 08:30 local |
| D1 Night Anchor modal UI | Mobile renders `display_mode=mobility_modal` and calls PUT mobility-intent on confirm |
| D2 in-app animations | Mobile renders animated summary card when `display_mode=summary` |
| D3 badge and progress badge | Mobile renders `display_mode=badge_prompt` with local badge count |
| D3 Premium Asset Lock paywall | Mobile renders lock screen on `display_mode=premium_asset_lock` |
| Local notification scheduling | Not used — all pushes are FCM server-sent |
| Language/gender selection | Resolved server-side from `users.language_code` and `user_profiles.gender`; mobile sends no language hint in push handling |

---

## Unresolved Questions

None.

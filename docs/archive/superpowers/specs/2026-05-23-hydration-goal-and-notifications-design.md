# Hydration Goal Calculation & Notifications Design

**Date:** 2026-05-23
**Status:** Approved

---

## Overview

Two related features:
1. **Dynamic hydration goal** — calculate a user's daily water target from their weight (35ml/kg), auto-updating when weight changes, with optional manual override.
2. **Smart hydration reminders** — two daily push notifications (1pm and 6pm, user local time) that fire only if the user is behind their hydration goal.

---

## Feature 1: Hydration Goal Calculation

### Goal Resolution

Goal is always computed at query time — never stored as a derived value:

```python
def resolve_hydration_goal_ml(profile: UserProfileDomainModel) -> int:
    return profile.custom_hydration_goal_ml or round(35 * profile.weight_kg)
```

- Override takes priority. If `custom_hydration_goal_ml` is `None`, weight-based formula applies.
- Used in `GetDailyHydrationQueryHandler` and `GetWeeklyHydrationQueryHandler` — replaces the existing `TODO` / hardcoded 2000ml default.

### Data Model

**Migration:** Add `custom_hydration_goal_ml: Optional[int]` to `user_profiles` table.
- `NULL` = use weight-based calculation
- Constraint: `> 0` when set

**Domain model:** Add `custom_hydration_goal_ml: Optional[int] = None` to `UserProfileDomainModel`.

### User Override

No new command needed. `UpdateUserProfileCommand` already handles profile field updates. Expose `custom_hydration_goal_ml: Optional[int]` in the profile update request schema. Setting to `null` resets to weight-based.

### Weight Change Behaviour

Because goal is computed from current `weight_kg` at query time, weight updates are reflected automatically on the next hydration query. Cache TTL is 5 minutes — brief staleness is acceptable. No event handler needed for weight changes.

Override is always respected: `resolve_hydration_goal_ml` checks `custom_hydration_goal_ml` first, so users with a manual override are never affected by weight changes.

### Cache Invalidation on Override Change

When `custom_hydration_goal_ml` changes via profile update, a new event handler listens to `UserProfileUpdatedEvent` and invalidates `user:{id}:hydration:{date}` and `user:{id}:hydration_weekly:{week_start}` cache keys when `custom_hydration_goal_ml` is in `updated_fields`.

---

## Feature 2: Smart Hydration Reminders

### Notification Types

Add two values to `NotificationType` enum:
- `HYDRATION_REMINDER_AFTERNOON` — scheduled at 13:00 user local time
- `HYDRATION_REMINDER_EVENING` — scheduled at 18:00 user local time

### Preferences

Add `hydration_reminders_enabled: bool = True` to:
- `NotificationPreferences` domain model (and `create_default()`)
- `NotificationPreferencesORM` table
- `GetNotificationPreferencesQuery` response
- `UpdateNotificationPreferencesCommand`

**Migration:** Add `hydration_reminders_enabled BOOLEAN NOT NULL DEFAULT TRUE` to `notification_preferences` table.

### Pre-Compute Phase (Midnight)

`DailyContextPrecomputeService` is extended to bulk-insert two hydration reminder rows per user per timezone alongside existing meal reminder rows — only when `hydration_reminders_enabled = True`.

| Type | Local Time | `scheduled_for_utc` |
|---|---|---|
| `HYDRATION_REMINDER_AFTERNOON` | 13:00 | 13:00 local → UTC |
| `HYDRATION_REMINDER_EVENING` | 18:00 | 18:00 local → UTC |

Context JSONB stored at midnight: `{fcm_tokens, gender, language_code}` — no hydration data, because progress must be evaluated live at send time.

The existing UNIQUE constraint on `(user_id, notification_type, scheduled_date)` ensures idempotent pre-compute.

### Send Phase (Live Check)

The existing send loop claims `status='pending'` rows past `scheduled_for_utc`. For hydration types, a pre-send check is added:

1. Fetch `consumed_ml` via `hydration_repository.sum_credited_ml_for_date(user_id, today_local)`
2. Fetch user profile → compute `goal_ml` via `resolve_hydration_goal_ml(profile)`
3. Evaluate threshold:
   - `HYDRATION_REMINDER_AFTERNOON`: skip FCM if `consumed_ml >= 0.5 × goal_ml`
   - `HYDRATION_REMINDER_EVENING`: skip FCM if `consumed_ml >= 0.8 × goal_ml`
4. Mark row `sent` regardless of whether FCM was called — prevents retry, keeps the table clean for tomorrow.

### Message Copy

New entries in `notification_messages.py` for both types, English + Vietnamese, gender-aware.

Example (English):
- Afternoon: *"You're halfway through the day — time to check your water intake!"*
- Evening: *"Almost there! A little more water could help you hit your daily goal."*

### Preference Toggle Behaviour

When `hydration_reminders_enabled` is set to `False`:
- No rows are created at the next midnight pre-compute.
- Any rows already created for the current day are not retroactively cancelled — they will be evaluated by the live check and marked `sent` naturally. Acceptable UX since the check is cheap.

---

## Architecture Summary

```
weight update  ─────────────────────────────────────────────┐
                                                             │
profile query → resolve_hydration_goal_ml(profile)          │
                ├── custom_hydration_goal_ml (if set)        │
                └── round(35 × weight_kg) (default)   ←─────┘

midnight precompute
  DailyContextPrecomputeService
  └── INSERT hydration_reminder rows (afternoon + evening)
        only if hydration_reminders_enabled = True

send loop (every 60s / cron)
  ScheduledNotificationService._send_due_notifications
  └── for HYDRATION_REMINDER_* rows:
        fetch consumed_ml (live)
        compute goal_ml
        check threshold → send or skip
        mark sent
```

---

## Files to Create / Modify

| Action | File |
|---|---|
| New migration | `alembic/versions/<ts>_add_custom_hydration_goal_ml.py` |
| New migration | `alembic/versions/<ts>_add_hydration_reminders_enabled.py` |
| Modify | `src/domain/model/user/core_user.py` |
| Modify | `src/domain/model/notification/notification_preferences.py` |
| Modify | `src/domain/model/notification/notification_enums.py` |
| New helper | `src/domain/services/hydration_goal_service.py` |
| Modify | `src/app/handlers/query_handlers/get_daily_hydration_query_handler.py` |
| Modify | `src/app/handlers/query_handlers/get_weekly_hydration_query_handler.py` |
| New event handler | `src/app/handlers/event_handlers/hydration_goal_cache_invalidation_event_handler.py` |
| Modify | `src/api/schemas/request/profile_requests.py` |
| Modify | `src/infra/database/models/user/profile.py` |
| Modify | `src/infra/database/models/notification/notification_preferences.py` |
| Modify | `src/infra/database/models/notification/notification.py` |
| Modify | `src/infra/services/daily_context_precompute_service.py` |
| Modify | `src/infra/services/scheduled_notification_service.py` |
| Modify | `src/domain/services/notification_messages.py` |
| Modify | `src/api/dependencies/event_bus.py` |

---

## Testing

### Unit Tests

- `resolve_hydration_goal_ml` — weight-based formula, override respected, edge weights
- `GetDailyHydrationQueryHandler` — goal reflects weight, goal reflects override, cache hit path
- `GetWeeklyHydrationQueryHandler` — same goal logic
- Threshold logic — afternoon at exactly 50%, evening at exactly 80%, above and below each

### Integration Tests

- Profile update with `custom_hydration_goal_ml` — persists, `null` resets to weight-based
- `UserProfileUpdatedEvent` with `custom_hydration_goal_ml` in `updated_fields` → hydration cache keys invalidated
- `DailyContextPrecomputeService` — creates two hydration rows when `hydration_reminders_enabled=True`, skips when `False`
- Send loop — row above threshold → `sent`, no FCM; below threshold → FCM called, `sent`

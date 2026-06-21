---
phase: 3
title: "Push Rendering and Payloads"
status: pending
effort: "1.5d"
priority: P1
dependencies: ["./phase-02-campaign-state-and-scheduler.md"]
---

# Phase 3: Push Rendering and Payloads

## Overview

Render the seven campaign notifications and send stable mobile routing data through the existing FCM dispatch path.

## Implementation Steps

1. Add a focused campaign message catalog instead of growing `notification_messages.py` much further.
2. Teach `CronNotificationDispatchService` to render campaign types and pass campaign payload fields to FCM.
3. Keep `notification_ids` and `notification_count` behavior unchanged for analytics and row status tracking.
4. Add fresh send-time reads for D2 summary, hydration, and movement values where the copy needs current state.
5. Add generic fallback copy when movement steps or hydration values are unavailable.
6. Ensure D3 copy uses "locked" or "unavailable" wording, not deletion claims.
7. Keep existing meal, hydration, daily summary, and trial rendering unchanged.

## Related Files

- `src/domain/services/onboarding_retention_messages.py`
- `src/domain/services/notification_messages.py`
- `src/infra/services/cron_notification_dispatch_service.py`
- `src/infra/services/push/android_payload_builder.py`
- `src/infra/services/push/apns_payload_builder.py`

## Base FCM Data Payload

```json
{
  "type": "d2_lunch_refuel",
  "notification_ids": "...",
  "notification_count": "1",
  "campaign": "onboarding_d1_d3",
  "campaign_day": "2",
  "campaign_step": "lunch_refuel",
  "deeplink": "nutree://today-log",
  "display_mode": "fast_log"
}
```

## Per-Type Routing Contract

| Type | Deeplink | Display mode |
|---|---|---|
| `d1_night_anchor` | `nutree://retention/mobility-intent` | `mobility_modal` |
| `d2_morning_steps_sync` | `nutree://today-log/morning` | `steps_sync` |
| `d2_lunch_refuel` | `nutree://today-log` | `fast_log` |
| `d2_hydration_slump` | `nutree://hydration` | `hydration_charge` |
| `d2_daily_summary` | `nutree://daily-summary` | `summary` |
| `d3_churn_preemption` | `nutree://progress-warning` | `badge_prompt` |
| `d3_premium_asset_lock` | `nutree://premium/asset-lock` | `premium_asset_lock` |

## Dynamic Copy Inputs

- Morning steps: use `movement_entries` if mobile has synced an entry before send time; otherwise generic morning copy.
- Hydration slump: use current-day `hydration_entries`; skip real-time Gemini and use a prewritten/cached tip pool.
- D2 summary: reuse the existing daily summary branches: `zero_logs`, `on_target`, `under_goal`, `slightly_over`, `way_over`.
- Asset lock: use asset summary counts from Phase 04 where available; otherwise render safe generic copy.

## Dispatch Constraints

- Do not send directly from the scheduler.
- Do not store recipient truth inside campaign state. Continue resolving active FCM tokens through the queue context and dispatch behavior already in place.
- If push builders have APNs badge support, send badge intent for `d3_churn_preemption`; mobile still owns final badge behavior.

## Success Criteria

- [ ] All seven campaign types render in supported languages/genders with safe fallback.
- [ ] FCM payload includes the stable routing keys mobile needs.
- [ ] Existing notification types still render with their current payload behavior.
- [ ] Dynamic values are fresh where needed and degrade gracefully when unavailable.
- [ ] Open questions: none.

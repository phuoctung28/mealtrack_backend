---
type: brainstorm
date: 260621-2125
status: approved-for-planning
topic: d1-d3-retention-campaign
---

# D1-D3 Retention Campaign Brainstorm

## Summary

Build a fixed D1-D3 onboarding retention campaign first. Ignore PM-editable notification admin for now.

D1 means the same local calendar day the user completes onboarding.

Use the existing DB-backed `notifications` queue and push cron. Do not send directly from request handlers. Do not use Redis for notification scheduling or context.

## Problem

The PO spec describes 7 push notifications across D1-D3, but the actual feature is bigger than copy. It includes:

- lifecycle-day scheduling
- mobile deep links and screen behavior
- backend state for user choices
- optional health sync inputs
- trial conversion / premium asset messaging

Treat this as a campaign lifecycle feature, not just notification content.

## Current Codebase Constraints

- Current push content is hardcoded in `src/domain/services/notification_messages.py`.
- Current queue model is `notifications` with uniqueness on `(user_id, notification_type, scheduled_date)`.
- Current push cron creates notification rows, dispatches due rows through FCM, and marks sent/failed/retry.
- Current precompute handles daily meal, summary, and hydration reminders.
- Current trial push schedules `trial_expiry_1d` roughly 2 hours before charge.
- Admin pattern exists through `require_admin`, but PM-editable admin is out of scope for this round.
- Notification context and FCM token ownership should remain database-owned.

## Requirements

1. Schedule 7 campaign pushes relative to onboarding completion.
2. D1 is onboarding completion local date, not next day.
3. Insert campaign rows into the existing `notifications` queue.
4. Preserve dedupe, retry, stale-processing reclaim, and FCM token handling.
5. Include mobile routing payloads for each push.
6. Keep micro-feature behavior explicit and separately testable.
7. Avoid false claims about deleting user data after trial.

## Campaign Schedule

| Step | Type | Local trigger |
|---|---|---|
| 1 | `d1_night_anchor` | D1 21:00 |
| 2 | `d2_morning_steps_sync` | D2 08:30 |
| 3 | `d2_lunch_refuel` | D2 11:45 |
| 4 | `d2_hydration_slump` | D2 15:00 |
| 5 | `d2_daily_summary` | D2 20:00 |
| 6 | `d3_churn_preemption` | D3 09:00 |
| 7 | `d3_premium_asset_lock` | 6 hours before trial ends |

## Evaluated Approaches

### Approach A: hardcode 7 notifications into existing daily precompute

Pros:
- fastest local change
- minimal new files

Cons:
- mixes daily reminders with onboarding lifecycle campaign
- hard to reason about D1-D3 eligibility
- awkward for D3 trial-relative timing

Verdict: reject. Too tangled.

### Approach B: dedicated D1-D3 campaign scheduler phase in push cron

Pros:
- preserves current queue/dispatch safety
- clean boundary for lifecycle eligibility
- supports D1 same-day rules and D3 trial-relative timing
- easy to feature-flag or disable later

Cons:
- needs new model/query logic
- needs focused tests around timezone and dedupe

Verdict: recommended.

### Approach C: external campaign platform or PM-editable campaign builder

Pros:
- high flexibility
- PM can experiment without deploys

Cons:
- overkill now
- requires admin UI, approval workflow, targeting DSL, variable validation, and safety tooling

Verdict: defer.

## Recommended Design

Create a dedicated campaign scheduler that runs as an extra phase in `src/cron/push.py` before dispatch.

The scheduler finds users who completed onboarding and have active FCM tokens, computes their campaign local dates from user timezone, and inserts due future notification rows into `notifications`.

Rows should be idempotent. Use `ON CONFLICT DO NOTHING` against `(user_id, notification_type, scheduled_date)`.

## Data Model

Prefer a small durable state table:

`onboarding_retention_state`

Fields:
- `id`
- `user_id`
- `campaign_started_at`
- `campaign_timezone`
- `tomorrow_mobility_type`
- `created_at`
- `updated_at`

Optional sent timestamps can be omitted if `notifications` remains source of truth for send status. Add them only if product needs a separate campaign audit view.

## Notification Context

Each inserted notification should include:

- `fcm_tokens`
- `gender`
- `language_code`
- `campaign_day`
- `campaign_step`
- `deeplink`
- `display_mode`
- dynamic values needed for rendering when available

Use send-time DB reads for values that must be fresh, such as daily summary calories or hydration progress.

## Mobile Payload Contract

Base payload:

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

Suggested per-type routing:

| Type | Deeplink | Display mode |
|---|---|---|
| `d1_night_anchor` | `nutree://retention/mobility-intent` | `mobility_modal` |
| `d2_morning_steps_sync` | `nutree://today-log/morning` | `steps_sync` |
| `d2_lunch_refuel` | `nutree://today-log` | `fast_log` |
| `d2_hydration_slump` | `nutree://hydration` | `hydration_charge` |
| `d2_daily_summary` | `nutree://daily-summary` | `summary` |
| `d3_churn_preemption` | `nutree://progress-warning` | `badge_prompt` |
| `d3_premium_asset_lock` | `nutree://premium/asset-lock` | `premium_asset_lock` |

## Backend Micro-Features

### Night Anchor

Backend stores:
- `tomorrow_mobility_type`

Need endpoint:
- `PUT /v1/retention/onboarding/mobility-intent`

Allowed values:
- `public_transit`
- `motorbike`
- `car_taxi`

### Morning Steps Sync

Mobile should own HealthKit / Health Connect pull.

Backend should only use synced steps if already available. Do not block push send waiting for mobile background sync.

### Lunch Fast Log

Needs either:
- reuse existing manual meal endpoint with preset payloads from mobile, or
- add a dedicated fast-log endpoint.

Recommended: reuse manual meal path if possible. New fast-log endpoint only if existing path is too heavy for 1-tap.

### Hydration Slump

Backend can deep link to hydration. Mobile owns animation and haptics.

Fortune-cookie AI tip should not call Gemini at tap time in v1. Use a small prewritten/cached tip pool first.

### D2 Daily Summary

Reuse existing daily summary branch logic:
- `zero_logs`
- `on_target`
- `under_goal`
- `slightly_over`
- `way_over`

Change trigger to D2 20:00 for campaign summary, separate from normal daily summary at 21:00 to avoid duplicate messaging.

### D3 Churn Preemption

Send badge fields in FCM/APNs config if supported. Mobile owns final badge behavior.

### D3 Premium Asset Lock

Backend can expose an asset summary endpoint:
- meal scan count
- steps synced
- hydration wins
- streak / active days

Copy must say progress may become locked/unavailable, not deleted, unless deletion is actually true.

## Risks

| Risk | Mitigation |
|---|---|
| Duplicate normal + campaign summaries | Separate types and suppress normal daily summary for D2 campaign users if needed. |
| Timezone bugs around late onboarding | D1 local date is based on user timezone at onboarding completion. If D1 21:00 has passed, skip D1 Night Anchor. |
| Health sync unavailable | Push still sends generic copy; no hard dependency on background OS task. |
| Premium copy overpromises deletion | Use locked/unavailable language. |
| Mobile and backend contracts drift | Freeze payload table before implementation. |
| Campaign state bloats notification code | New dedicated scheduler service, not inside daily precompute builder. |

## Success Criteria

- User completing onboarding before 21:00 local gets D1 Night Anchor same local day.
- User completing onboarding after 21:00 local does not get stale D1 Night Anchor.
- D2 and D3 rows are inserted once per user/type/date.
- Push cron still dispatches through existing queue and FCM path.
- Payloads include stable `type`, `deeplink`, `campaign_day`, `campaign_step`, and `display_mode`.
- Hydration, daily summary, and trial asset notifications render with live or accurate-enough values.
- Existing meal reminders, hydration reminders, daily summary, and trial expiry behavior do not regress.

## Recommended Phases

1. Backend campaign scheduler and notification row insertion.
2. Push rendering and payload contracts for 7 campaign types.
3. Minimal backend state endpoints for mobility and asset summary.
4. Mobile deep links and campaign screens.
5. Optional health sync / fast-log refinements.

## Out Of Scope

- PM-editable notification admin.
- Arbitrary campaign builder.
- Redis notification scheduling.
- Real-time Gemini call after hydration tap.
- Any claim that trial cancellation deletes data unless product behavior is changed.

## Unresolved Questions

- Should normal meal reminders still fire during D1-D3, or should campaign pushes temporarily replace them?
- Does mobile already have a deep-link router that can support the proposed routes?
- Should D3 asset lock use RevenueCat trial end time only, or app-side campaign start plus 72 hours when RevenueCat data is missing?

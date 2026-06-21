---
phase: 4
title: "Backend Micro-feature APIs"
status: pending
effort: "1d"
priority: P1
dependencies: ["./phase-02-campaign-state-and-scheduler.md"]
---

# Phase 4: Backend Micro-feature APIs

## Overview

Expose the small backend contracts the mobile D1-D3 experience needs without building the deferred PM notification editor.

## Implementation Steps

1. Add route module `src/api/routes/v1/retention.py` and register it in the API router.
2. Add request/response schemas for onboarding retention payloads.
3. Add `PUT /v1/retention/onboarding/mobility-intent`.
4. Add `GET /v1/retention/onboarding/asset-summary`.
5. Reuse the existing manual meal path for Lunch Fast Log if mobile can submit preset meal payloads there.
6. Do not add a fast-log endpoint unless the existing manual meal route is proven too heavy.
7. Add auth checks through `get_current_user_id`; no admin surface in this phase.

## Mobility Intent Endpoint

```http
PUT /v1/retention/onboarding/mobility-intent
```

Request:

```json
{
  "tomorrow_mobility_type": "public_transit"
}
```

Allowed values:

- `public_transit`
- `motorbike`
- `car_taxi`

Behavior:

- Upsert into `onboarding_retention_states.tomorrow_mobility_type`.
- If no campaign state exists but the user has completed onboarding, create the state idempotently with current time and timezone.
- Reject the request if the user has not completed onboarding.

## Asset Summary Endpoint

```http
GET /v1/retention/onboarding/asset-summary
```

Suggested response:

```json
{
  "meal_scan_count": 3,
  "hydration_entry_count": 4,
  "hydration_win_count": 1,
  "movement_entry_count": 2,
  "active_day_count": 2,
  "trial_end_at": "2026-06-24T14:00:00Z",
  "lock_at": "2026-06-24T08:00:00Z"
}
```

Data sources:

- Meals from existing meal tables, scoped from `campaign_started_at` through now.
- Hydration from `hydration_entries`.
- Movement from `movement_entries`; current backend stores movement entries, not raw step counts, so mobile should send synced step activity if step-specific display is required.
- Trial end from `subscriptions.expires_at` or fallback `campaign_started_at + 72h`.

Mobile-owned behavior:

- HealthKit / Health Connect background pull at D2 08:15.
- D1 mobility modal UI.
- D2 hydration animation and haptics.
- D3 persistent badge display.
- Full-screen premium lock UI and delayed dismissal friction.

## Success Criteria

- [ ] Authenticated users can store mobility intent only for their own campaign.
- [ ] Asset summary is scoped to the current user and campaign window.
- [ ] APIs do not expose admin notification editing.
- [ ] Fast-log remains on the existing meal path unless proven impossible.
- [ ] Open questions: none.

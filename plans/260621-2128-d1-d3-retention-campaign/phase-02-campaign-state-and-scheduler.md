---
phase: 2
title: "Campaign State and Scheduler"
status: pending
effort: "2d"
priority: P1
dependencies: ["./phase-01-contract-and-regression-tests.md"]
---

# Phase 2: Campaign State and Scheduler

## Overview

Persist the campaign start moment at onboarding completion and add a dedicated cron scheduler phase that inserts the seven D1-D3 notification rows into the existing `notifications` queue.

## Implementation Steps

1. Add migration `migrations/versions/<timestamp>_add_onboarding_retention_state.py`.
2. Add ORM model `src/infra/database/models/notification/onboarding_retention_state.py` and export it from model package init files.
3. Add repository/service helpers for idempotent state initialization and campaign row insertion.
4. Initialize campaign state from `CompleteOnboardingCommandHandler` when `onboarding_completed` flips from false to true.
5. Add `OnboardingRetentionCampaignScheduler` under `src/infra/services/`.
6. Wire scheduler into `src/cron/push.py` after daily precompute/trial scheduling and before dispatch.
7. Suppress pending normal `daily_summary` rows for campaign D2 user/date when inserting `d2_daily_summary`.
8. Keep all scheduling DB-backed; do not introduce Redis state.

## Data Model

```text
onboarding_retention_states
- id
- user_id unique, FK users.id on delete cascade
- campaign_started_at timestamptz not null
- campaign_timezone varchar not null
- tomorrow_mobility_type varchar nullable
- created_at timestamptz not null
- updated_at timestamptz not null
```

## Initialization Rules

- Use the existing onboarding completion boundary: `src/app/handlers/command_handlers/complete_onboarding_command_handler.py`.
- Only create the state row when onboarding transitions from incomplete to complete.
- Capture `campaign_started_at = utc_now()` and `campaign_timezone = user.timezone or "UTC"` at that moment.
- If a row already exists, leave `campaign_started_at` unchanged.
- Do not infer campaign start later from `users.last_accessed`; that field is not a durable onboarding-completion timestamp.

## Scheduler Rules

- Query active campaign states whose local campaign window can still have unscheduled D1-D3 rows.
- Fetch user timezone, language, gender, notification preferences, active FCM tokens, subscription expiry, calories/hydration/movement summary inputs as needed.
- Build rows for:
  - `d1_night_anchor` at D1 21:00 local, only if not stale.
  - `d2_morning_steps_sync` at D2 08:30 local.
  - `d2_lunch_refuel` at D2 11:45 local.
  - `d2_hydration_slump` at D2 15:00 local.
  - `d2_daily_summary` at D2 20:00 local.
  - `d3_churn_preemption` at D3 09:00 local.
  - `d3_premium_asset_lock` at `(subscription.expires_at or campaign_started_at + 72h) - 6h`.
- Convert local triggers to UTC with `zoneinfo.ZoneInfo`.
- Insert rows with PostgreSQL `ON CONFLICT DO NOTHING` against the existing unique key.
- Keep `notification_type` values under the existing 30-character column limit.

## Normal Summary Suppression

- When `d2_daily_summary` is inserted, delete only pending normal `daily_summary` rows for the same user and local scheduled date.
- Never delete sent, failed, processing, meal reminder, hydration reminder, or trial rows.

## Success Criteria

- [ ] Campaign state is initialized exactly once when onboarding completes.
- [ ] Re-running cron does not duplicate campaign notification rows.
- [ ] D1 late-onboarding users skip stale D1 and still receive D2/D3.
- [ ] D2 campaign summary prevents duplicate normal summary for that local date.
- [ ] Existing `src/cron/push.py` dispatch and cleanup phases still run.
- [ ] Open questions: none.

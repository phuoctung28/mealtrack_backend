---
title: "D1-D3 Retention Campaign"
description: "Schedule and dispatch a fixed D1-D3 onboarding retention campaign through the existing notification queue with backend payload contracts and mobile handoff."
status: pending
priority: P1
branch: "delivery"
tags: [feature, notifications, cron, retention, mobile-contract]
effort: "5-7d"
blockedBy: []
blocks: []
created: "2026-06-21T14:28:58.799Z"
createdBy: "ck:plan"
source: skill
---

# D1-D3 Retention Campaign

## Overview

Build the fixed onboarding retention campaign from the PO spec. This is not the PM-editable notification builder; that V1 is explicitly out of scope for now.

Use the existing DB-backed `notifications` queue and `src/cron/push.py` dispatch path. D1 means the same local calendar day the user completes onboarding. If the user completes onboarding after the D1 21:00 local trigger, skip the stale D1 Night Anchor and continue with D2/D3.

Defaults locked from brainstorm:

- Keep normal meal reminders.
- Suppress the normal daily summary on campaign D2 to avoid duplicate summary pushes.
- Include backend and mobile contract work in the plan.
- For `d3_premium_asset_lock`, use RevenueCat `subscriptions.expires_at` as the trial end when available; otherwise use `campaign_started_at + 72h` as the trial end and schedule 6 hours before it.

Source report: `../reports/260621-2125-d1-d3-retention-campaign-brainstorm.md`

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Contract and Regression Tests](./phase-01-contract-and-regression-tests.md) | Pending |
| 2 | [Campaign State and Scheduler](./phase-02-campaign-state-and-scheduler.md) | Pending |
| 3 | [Push Rendering and Payloads](./phase-03-push-rendering-and-payloads.md) | Pending |
| 4 | [Backend Micro-feature APIs](./phase-04-backend-micro-feature-apis.md) | Pending |
| 5 | [Verification and Mobile Handoff](./phase-05-verification-and-mobile-handoff.md) | Pending |

## Dependencies

No cross-plan dependency. Existing pending bandwidth reduction plan is unrelated.

Implementation depends on:

- Existing notification queue: `src/infra/database/models/notification/notification.py`
- Existing push cron: `src/cron/push.py`
- Existing dispatch service: `src/infra/services/cron_notification_dispatch_service.py`
- Existing notification copy catalog: `src/domain/services/notification_messages.py`
- Existing onboarding completion boundary: `src/app/handlers/command_handlers/complete_onboarding_command_handler.py`
- Existing trial expiry source: `src/infra/database/models/subscription.py`

## Out of Scope

- PM-editable notification admin.
- Arbitrary campaign builder, targeting DSL, preview workflow, or approval workflow.
- Redis-backed notification scheduling.
- Real-time Gemini call for hydration fortune-cookie copy.
- Copy that claims user data is deleted after trial.

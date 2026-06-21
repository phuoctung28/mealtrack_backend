---
phase: 1
title: "Contract and Regression Tests"
status: pending
effort: "1d"
priority: P1
dependencies: []
---

# Phase 1: Contract and Regression Tests

## Overview

Write failing tests first for the D1-D3 retention campaign contracts, then keep existing notification behaviors protected while later phases change scheduling and rendering.

## Implementation Steps

1. Add scheduler contract tests for D1 same-local-day timing, D1 stale skip after 21:00 local, D2 fixed local times, and D3 trial-end-minus-6h timing.
2. Add idempotency tests proving repeated cron runs insert each campaign row once through `(user_id, notification_type, scheduled_date)`.
3. Add dispatch payload tests for campaign data keys: `type`, `notification_ids`, `notification_count`, `campaign`, `campaign_day`, `campaign_step`, `deeplink`, `display_mode`.
4. Add regression tests that normal meal reminders still schedule and dispatch.
5. Add a regression test that campaign D2 suppresses the normal `daily_summary` row for that user/date only.
6. Add D3 fallback tests: RevenueCat `expires_at` wins; missing `expires_at` falls back to `campaign_started_at + 72h`.
7. Add API contract tests for the minimal retention endpoints planned in Phase 04.

## Related Files

- `tests/unit/infra/services/test_onboarding_retention_campaign_scheduler.py`
- `tests/unit/infra/test_cron_notification_dispatch_service.py`
- `tests/unit/cron/test_push_cron.py`
- `tests/unit/domain/services/test_notification_messages.py`
- `tests/unit/api/routes/test_retention_routes.py`
- `tests/fixtures/fakes/fake_notification_repository.py` if a fake needs campaign helpers.

## Key Scenarios

- D1 is the onboarding completion local date, not "tomorrow".
- D1 Night Anchor schedules at 21:00 local only when that time has not passed.
- D2 sends at 08:30, 11:45, 15:00, and 20:00 local.
- D3 churn preemption sends at 09:00 local.
- D3 asset lock sends 6 hours before trial end.
- Rows are inserted into `notifications`; request handlers never send FCM directly.
- Users without active FCM tokens do not get queued rows.
- Existing trial expiry push behavior remains intact unless the campaign row deliberately supersedes it for the same product moment.

## Validation Command

```bash
uv run pytest tests/unit/infra/services/test_onboarding_retention_campaign_scheduler.py tests/unit/infra/test_cron_notification_dispatch_service.py tests/unit/cron/test_push_cron.py tests/unit/domain/services/test_notification_messages.py tests/unit/api/routes/test_retention_routes.py -q
```

## Success Criteria

- [ ] Tests fail before implementation for new campaign behavior.
- [ ] Existing notification regressions are represented in tests.
- [ ] Test fixtures cover at least one non-UTC timezone.
- [ ] Test cases cover duplicate cron runs.
- [ ] Open questions: none.

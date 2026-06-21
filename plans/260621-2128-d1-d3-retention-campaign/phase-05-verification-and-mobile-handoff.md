---
phase: 5
title: "Verification and Mobile Handoff"
status: pending
effort: "0.5-1d"
priority: P1
dependencies: ["./phase-01-contract-and-regression-tests.md", "./phase-02-campaign-state-and-scheduler.md", "./phase-03-push-rendering-and-payloads.md", "./phase-04-backend-micro-feature-apis.md"]
---

# Phase 5: Verification and Mobile Handoff

## Overview

Verify the backend behavior end to end and leave mobile with a precise payload and endpoint contract.

## Implementation Steps

1. Run focused unit/API tests for campaign scheduler, dispatch payloads, message rendering, and retention routes.
2. Run compile/syntax verification with the repo toolchain.
3. Run a migration sanity check against the Alembic head.
4. Produce `reports/mobile-payload-contract.md` inside this plan folder.
5. Document mobile implementation responsibilities and backend assumptions.
6. Confirm no PM-editable notification files or admin routes were added.
7. Record docs impact before handoff.

## Verification Commands

```bash
uv run pytest tests/unit/infra/services/test_onboarding_retention_campaign_scheduler.py tests/unit/infra/test_cron_notification_dispatch_service.py tests/unit/cron/test_push_cron.py tests/unit/domain/services/test_notification_messages.py tests/unit/api/routes/test_retention_routes.py -q
uv run python -m compileall src tests
uv run alembic heads
```

Run broader tests if campaign work touches shared notification or onboarding behavior:

```bash
uv run pytest tests/unit/infra/test_daily_context_precompute_service.py tests/unit/infra/services/test_cron_trial_push_service.py tests/unit/api/test_routes_with_mocked_event_bus.py -q
```

## Mobile Handoff Contract Must Include

- Seven notification types and exact local trigger rules.
- FCM data payload contract and deep links.
- Endpoint contracts for mobility intent and asset summary.
- D1 stale rule: if onboarding completion is after 21:00 local, backend skips D1 Night Anchor.
- D2 summary duplicate rule: backend suppresses normal daily summary for campaign D2 only.
- Health sync rule: mobile syncs movement/steps before D2 08:30; backend sends generic copy if no data arrived.
- Trial timing rule: backend uses `subscriptions.expires_at`; fallback trial end is `campaign_started_at + 72h`; asset lock push schedules 6 hours before trial end.
- Copy safety rule: locked/unavailable language only, no deletion claim.

## Docs Impact

- Minor if only plan/report files are produced.
- Major once implementation lands, because notification behavior and mobile contracts should be reflected in `docs/api-endpoints.md` or the current API docs index.

## Success Criteria

- [ ] Focused tests pass.
- [ ] Compile/syntax verification passes.
- [ ] Migration head check passes.
- [ ] Mobile handoff report exists and matches backend payloads.
- [ ] No PM-editable notification builder work slipped into scope.
- [ ] Open questions: none.

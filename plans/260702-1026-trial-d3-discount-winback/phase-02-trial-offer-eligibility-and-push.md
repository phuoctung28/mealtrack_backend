---
phase: 2
title: "Trial offer eligibility and push"
status: completed
priority: P1
effort: "0.5d"
dependencies: [1]
---

# Phase 2: Trial offer eligibility and push

## Context Links

- Trial push service: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/services/cron_trial_push_service.py`
- Subscription repository: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/repositories/subscription_repository_async.py`
- Dispatch service: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/services/cron_notification_dispatch_service.py`
- Message templates: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/notification_messages.py`
- Push cron: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/cron/push.py`

## Overview

Extend the existing trial-expiry push job to target all near-D3 trial users who have not claimed the discount, including users who cancelled auto-renew but still have trial access.

## Key Insights

- Current service already inserts one `trial_expiry_1d` row and dispatch maps it to mobile `data.type=trial_expiry`.
- Current repository method filters only `status='active'`, so cancellation-intent users are excluded.
- Current message copy is already service-oriented and has no price. Keep it that way.

## Requirements

- Functional: include active trials and cancelled-but-unexpired trials.
- Functional: exclude users who already claimed the trial-end discount.
- Functional: dedupe with existing notification uniqueness and sent log behavior.
- Functional: route mobile to existing `trial_expiry` notification type.
- Non-functional: no PostHog push dependency, no hardcoded price in push, no Firebase token logging.

## Architecture

`src/cron/push.py` phase 2 -> `CronTrialPushService` -> new subscription eligibility query -> `notifications` queue -> `CronNotificationDispatchService` -> FCM -> mobile `trial_expiry` route.

Timing recommendation: preserve current `expires_at - 2h` behavior for MVP. If product wants an earlier D3 morning nudge, make `_CHARGE_LEAD` configurable instead of hardcoding a second campaign.

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/services/cron_trial_push_service.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/repositories/subscription_repository_async.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/ports/subscription_repository_port.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/notification_messages.py` only if copy needs tuning
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/services/test_cron_trial_push_service.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/repositories/test_subscription_repository_async.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/test_cron_notification_dispatch_service.py`

## Implementation Steps

1. Add repository method `find_trial_end_offer_candidates(now, lookahead_days)` or equivalent.
2. Query rules:
   - `expires_at > now`
   - `expires_at < now + lookahead`
   - `status IN ('active', 'cancelled')`
   - `period_type='TRIAL'` or rollout fallback `purchased_at >= now - 7 days`
   - `trial_end_discount_claimed_at IS NULL`
3. Update `CronTrialPushService._schedule_due_pushes` to call the new eligibility method.
4. Keep notification type `trial_expiry_1d` unless a second timing is approved.
5. Add safe context keys such as `campaign='trial_end_discount'` and `subscription_id` only if needed for analytics. Do not include price.
6. Keep `_render_message` copy as service reminder, or lightly tune EN/VI copy without mentioning the discount.
7. Add tests for active trial, cancelled-unexpired trial, expired trial, already-claimed discount, no token, and duplicate scheduling.

## Todo List

- [x] Add eligibility repository method and port signature.
- [x] Update trial push service to use the new audience.
- [x] Preserve dedupe on `(user_id, notification_type, scheduled_date)`.
- [x] Add candidate and scheduling tests.
- [x] Update docs if final timing differs from current docs.

## Success Criteria

- [x] Cancelled-but-unexpired trial users can receive the D3 service reminder.
- [x] Users who claimed the discounted product do not receive the reminder.
- [x] Push payload continues to route mobile as `trial_expiry`.
- [x] Push copy contains no price or direct discount claim.

## Risk Assessment

- Risk: fallback `purchased_at >= now - 7 days` catches non-trial purchases. Mitigation: only use fallback for existing rows and prefer `period_type`.
- Risk: duplicate sends from cron concurrency. Mitigation: keep existing database unique constraint and row claiming.
- Risk: compliance drift. Mitigation: service reminder copy only; paywall shows price after user taps.

## Security Considerations

- Do not log FCM tokens or user email.
- Keep notification context as immutable render snapshot only.
- Do not add Redis state for eligibility.

## Next Steps

Phase 3 decides who sends winback email for cancellation-intent users.

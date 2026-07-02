---
phase: 3
title: "Cancellation email ownership and workflow"
status: completed
priority: P1
effort: "0.5d"
dependencies: [1]
---

# Phase 3: Cancellation email ownership and workflow

## Context Links

- RevenueCat webhook cancellation handler: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/webhooks.py`
- Email service: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/email_service.py`
- Disabled lifecycle email cron code: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/services/cron_lifecycle_email_service.py`
- PostHog adapter: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/adapters/posthog_adapter.py`
- Mobile PostHog identify includes email: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/core/observability/posthog_user_observer.dart`

## Overview

Make PostHog Workflow the cancellation winback email owner. Backend lifecycle email cron is disabled in infra and should not be extended; backend currently also has a separate immediate cancellation email inside the RevenueCat webhook, so implementation must gate or remove that path.

## Key Insights

- Backend already captures `subscription_cancelled` into PostHog with `period_type`, `cancel_reason`, and `expiration_at_ms`.
- Backend already has code to send `trial_cancelled` email from `handle_cancellation`, separate from the disabled email cron.
- PostHog email requires a verified channel and a person email property.

## Requirements

- Functional: make PostHog Workflow the default/target owner for cancellation winback email.
- Functional: backend must not send immediate Resend cancellation email when email infra is disabled or PostHog owns the flow.
- Functional: PostHog event properties must be enough to build workflow audience.
- Non-functional: do not add new behavior to the disabled email cron; verify PostHog unsubscribe behavior before launch.

## Architecture

RevenueCat `CANCELLATION` -> backend persists subscription state -> backend captures `subscription_cancelled` -> PostHog Workflow sends delayed winback email.

Recommended rollout: keep backend email sending off, create/QA PostHog Workflow in staging, then enable production workflow after verifying the webhook email path cannot send.

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/config/settings.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/webhooks.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/routes/test_webhooks_cancellation_email.py`
- Modify/Add: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/test_webhook_handler.py`
- Optional modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/email_service.py` if backend remains email owner
- External config: PostHog Workflow, email channel, and template

## Implementation Steps

1. Add `CANCELLATION_EMAIL_OWNER` setting with allowed values `posthog` and `off` if a switch is still useful; default to `posthog` for campaign ownership or `off` until the workflow is live.
2. Gate or remove `handle_cancellation` Resend call so disabled email infra cannot double-send.
3. Extend PostHog `subscription_cancelled` properties:
   - `period_type`
   - `cancel_reason`
   - `expiration_at_ms`
   - `days_until_expiration`
   - `trial_end_discount_claimed`
   - `email_owner`
4. Update cancellation email tests for PostHog-owned/off modes and the stale webhook Resend path.
5. Create PostHog Workflow:
   - Trigger: `subscription_cancelled`
   - Filters: `period_type = TRIAL`, `trial_end_discount_claimed != true`, `expiration_at_ms` in future, production only
   - Delay: short cooling-off delay, e.g. 15-60 minutes
   - Action: send winback email with CTA to app/paywall
6. Verify workflow sends only after PostHog channel is configured and backend email path is off.

## Todo List

- [x] Add email owner/kill-switch config if needed.
- [x] Gate or remove backend webhook cancellation email path.
- [x] Extend PostHog cancellation properties.
- [x] Update tests.
- [ ] Configure PostHog Workflow after channel verification.

## Success Criteria

- [x] A cancellation event cannot produce backend Resend email plus PostHog winback email.
- [x] PostHog audience can target trial cancellations that still have access.
- [x] Disabled lifecycle email cron is not extended.
- [x] Tests prove webhook email path is off when PostHog owns the flow.

## Risk Assessment

- Risk: PostHog person lacks email. Mitigation: verify identify flow before launch and monitor skipped workflow sends.
- Risk: unsubscribe semantics differ between backend and PostHog. Mitigation: verify before production owner switch.
- Risk: stale backend webhook email code still sends when infra changes. Mitigation: explicit config/test around `handle_cancellation`.

## Security Considerations

- Do not add email to backend PostHog lifecycle event unless privacy review approves.
- Keep cancellation event properties non-PII.
- Do not log email send failures with raw recipient address.

## Next Steps

Phase 4 makes the push/email CTA open the correct discounted paywall.

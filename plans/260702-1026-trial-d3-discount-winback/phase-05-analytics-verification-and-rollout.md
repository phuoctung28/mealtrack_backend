---
phase: 5
title: "Analytics verification and rollout"
status: in_progress
priority: P1
effort: "0.5d"
dependencies: [1, 2, 3, 4]
---

# Phase 5: Analytics verification and rollout

## Context Links

- Backend external services docs: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/external-services.md`
- Backend analytics adapter: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/adapters/posthog_adapter.py`
- Mobile analytics taxonomy: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/docs/analytics-taxonomy.md`
- Mobile paywall price guide: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/docs/paywall-price-ab-testing.md`

## Overview

Verify that the full campaign is observable, non-duplicative, and rollback-safe before production launch.

## Key Insights

- Mobile analytics docs say RevenueCat/App Store lifecycle is commercial truth.
- Backend docs currently mention T-2d/T-1d trial pushes, but current code schedules one `trial_expiry_1d` reminder about two hours before charge.
- Backend lifecycle email cron is disabled in infra and expected to be removed, so rollout verification should focus on PostHog Workflow email and the webhook email kill switch.
- PostHog Workflow setup is external config, so the plan must include manual verification gates.

## Requirements

- Functional: analytics distinguishes push reminder, paywall source, cancellation, discount claim, and paid conversion.
- Functional: docs describe the final owner/timing truth.
- Functional: rollout can be disabled by config/flag without app redeploy.
- Non-functional: no PII in logs or analytics properties beyond existing PostHog person email identify.

## Architecture

RevenueCat is source of truth. Backend emits lifecycle events and schedules pushes. Mobile emits paywall UX events with `source=trial_expiry` and offering ID. PostHog Workflow, if enabled, consumes backend `subscription_cancelled`.

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/external-services.md`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/codebase-summary.md` if feature summary changes
- Modify: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/docs/analytics-taxonomy.md`
- Modify: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/docs/paywall-price-ab-testing.md`
- Optional modify: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/core/services/analytics_service.dart`
- Optional modify: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/core/services/analytics_events.dart`

## Implementation Steps

1. Add or verify analytics properties:
   - push campaign: `trial_end_discount`
   - paywall source: `trial_expiry`
   - resolved `offering_id`
   - cancellation `period_type`, `cancel_reason`, `days_until_expiration`
   - discount claim state
2. Update docs to reflect final timing and owner:
   - backend push cron schedules one trial-end service reminder unless product chooses earlier D3 timing
   - cancellation winback email is PostHog-owned
   - backend lifecycle email cron is disabled/future removal
   - webhook cancellation email path is off or explicitly gated
3. Verification commands:
   - Backend targeted: `.venv/bin/pytest tests/unit/infra/services/test_cron_trial_push_service.py tests/unit/infra/repositories/test_subscription_repository_async.py tests/unit/api/routes/test_webhooks_cancellation_email.py tests/unit/api/test_webhook_handler.py -q`
   - Backend quality: `.venv/bin/ruff check src/infra/services/cron_trial_push_service.py src/infra/repositories/subscription_repository_async.py src/api/routes/v1/webhooks.py`
   - Mobile generated code: `dart run build_runner build --delete-conflicting-outputs`
   - Mobile quality: `flutter analyze && flutter test`
4. Staging QA:
   - RevenueCat sandbox trial start.
   - Cancel trial auto-renew, verify PostHog `subscription_cancelled`.
   - Verify user remains eligible for D3 push while unexpired.
   - Tap push, verify discount offering/paywall price.
   - Purchase discount, verify backend claim state.
   - Verify no duplicate email.
5. Production rollout:
   - Publish RevenueCat discount offering/products.
   - Set discount product ID config.
   - Enable mobile flag payload with `discount_offering_id`.
   - Verify PostHog email channel and enable workflow after confirming backend webhook email path is off.
   - Monitor 30-60 minutes for push schedules, paywall resolves, purchases, and cancellation email volume.
6. Rollback:
   - Disable PostHog Workflow and keep backend webhook email path off unless product explicitly re-enables backend email.
   - Remove/disable discount offering payload in PostHog flag.
   - Clear discount product config to stop claim targeting.

## Todo List

- [x] Add analytics/docs updates.
- [x] Run backend targeted tests and ruff.
- [x] Run mobile build_runner/analyze/tests.
- [ ] Complete staging RevenueCat/PostHog QA.
- [ ] Prepare production rollout and rollback checklist.

## Success Criteria

- [ ] End-to-end staging path proves cancellation user remains eligible until expiry.
- [x] Push opens localized discounted paywall.
- [x] Discount purchase marks claim and removes future eligibility.
- [x] No duplicate cancellation email.
- [x] Docs match final code behavior.

## Risk Assessment

- Risk: external RevenueCat/App Store products not approved. Mitigation: do not enable flag/config until products are live.
- Risk: PostHog workflow sends to sandbox/test users in prod. Mitigation: filter `environment != SANDBOX` and test with staging project first.
- Risk: metrics mismatch between client purchase success and RevenueCat truth. Mitigation: report commercial conversion from RevenueCat/server lifecycle.

## Security Considerations

- Keep analytics properties non-PII.
- Do not expose discount eligibility secrets to unauthenticated routes.
- Keep RevenueCat webhook secret and PostHog API key in environment only.

## Next Steps

After this plan is approved, implement with `/ck:cook /Users/alexnguyen/Desktop/Nut/mealtrack_backend/plans/260702-1026-trial-d3-discount-winback/plan.md`.

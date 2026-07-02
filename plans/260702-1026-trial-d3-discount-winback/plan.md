---
title: "Trial D3 Discount Reminder and Cancellation Winback"
description: "Send trial-end service reminders to unconverted trial users, open a localized discounted paywall, and choose one cancellation winback email owner."
status: in_progress
priority: P1
effort: "2-3d"
branch: "main"
tags: [feature, backend, mobile, subscriptions, notifications, analytics]
blockedBy: []
blocks: []
created: "2026-07-02T03:26:46.507Z"
createdBy: "ck:plan"
source: skill
---

# Trial D3 Discount Reminder and Cancellation Winback

## Overview

Feasible. MealTrack already owns the hard parts: RevenueCat webhook state, FCM queue/dispatch, disabled lifecycle email code, and PostHog lifecycle mirroring. Nutree mobile already routes `trial_expiry` pushes to the subscription paywall and already reads RevenueCat offering IDs from PostHog payloads.

This plan keeps the push as a service reminder and lets the paywall reveal the localized discounted price. Do not hardcode `299k` in push/email copy. VN can show VND 299k because the RevenueCat/App Store product price says so; other storefronts show their local `StoreProduct.priceString`.

Core decisions:
- "Claimed offer" means server-confirmed discounted purchase/conversion, not local "saw offer". Mobile `discountOfferSeenKey` is device-local and not safe for backend audience selection.
- Trial-end audience must include active trials and cancelled-but-unexpired trials. Backend currently marks cancellation as `status='cancelled'` while access remains until `expires_at`, so the current `status='active'` expiry query would miss cancellation-intent users.
- PostHog Workflow is the intended cancellation winback email path. Backend lifecycle email cron is disabled in infra and expected to be removed, so do not build new campaign behavior on it. Still gate/remove the separate webhook cancellation-email path so it cannot double-send.
- Backend FCM remains push owner. PostHog Workflows can own email/segmentation, not mobile push.

Scope Challenge:
- Existing code: RevenueCat webhook, PostHog lifecycle capture, FCM notification queue, trial-expiry push, disabled lifecycle email code, mobile notification routing, RevenueCat offering-based paywall.
- Minimum change set: durable trial/claim fields, expanded eligibility query, one email-owner switch, mobile route/offering wiring, analytics/docs/tests.
- Complexity: cross-repo, about 10-14 files plus migration/tests. One small policy/helper is acceptable; no new campaign platform.
- Selected mode: `--hard` because subscription state + payment messaging + push/email compliance have high blast radius.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [RevenueCat lifecycle contract](./phase-01-revenuecat-lifecycle-contract.md) | Completed |
| 2 | [Trial offer eligibility and push](./phase-02-trial-offer-eligibility-and-push.md) | Completed |
| 3 | [Cancellation email ownership and workflow](./phase-03-cancellation-email-ownership-and-workflow.md) | Completed (code); PostHog workflow setup remains external |
| 4 | [Mobile discounted paywall routing](./phase-04-mobile-discounted-paywall-routing.md) | Completed |
| 5 | [Analytics verification and rollout](./phase-05-analytics-verification-and-rollout.md) | In Progress |

## Dependencies

- No unfinished backend plan blocks this work.
- Related mobile reference: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/plans/260621-2254-d1-d3-retention-campaign-mobile/plan.md`.
- External setup required before launch: RevenueCat discount offering/products published for every target storefront; PostHog email channel verified for winback email.
- Useful docs: [PostHog Workflows](https://posthog.com/docs/workflows), [PostHog workflow channels](https://posthog.com/docs/workflows/configure-channels), [RevenueCat webhook events](https://www.revenuecat.com/docs/integrations/webhooks/event-types-and-fields), [Apple notification guideline 4.5.4](https://developer.apple.com/app-store/review/guidelines/).

## Validation Log

- Verified backend trial push exists at `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/services/cron_trial_push_service.py:28`.
- Verified current trial query only selects active subscriptions at `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/repositories/subscription_repository_async.py:91`.
- Verified cancellation sets `status='cancelled'` but access remains until expiry at `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/webhooks.py:343`.
- Verified backend already mirrors `subscription_cancelled` with `period_type`, `cancel_reason`, and `expiration_at_ms` at `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/webhooks.py:454`.
- Verified backend already sends cancellation email via Resend at `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/webhooks.py:370`.
- Verified mobile routes `trial_expiry` notification taps to `/subscription-required?source=trial_expiry` at `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/notifications/application/notification_navigation_service.dart:26`.
- Verified mobile price-test payload supports `discount_offering_id` at `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/subscriptions/application/providers/paywall_price_test_provider.dart:9`.
- Verified mobile paywall displays localized RevenueCat product price strings at `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/subscriptions/application/providers/paywall_provider.dart:66`.
- Red-team findings recorded in `reports/red-team-review.md`; all accepted findings are mapped into phases.

---
title: "Cross-Repo Codebase Scout"
type: research
status: complete
created: 2026-07-02
---

# Cross-Repo Codebase Scout

## Summary

The plan should be backend-primary. MealTrack owns durable subscription state, FCM queueing, email, and RevenueCat/PostHog lifecycle events. Mobile mostly needs route-to-offering wiring and tests.

## Backend Evidence

- Push cron has trial scheduling, dispatch, and cleanup in `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/cron/push.py`.
- Trial push service inserts a single `trial_expiry_1d` notification about two hours before charge in `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/services/cron_trial_push_service.py`.
- Current expiry query only finds `Subscription.status == "active"` in `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/repositories/subscription_repository_async.py`.
- Cancellation marks the subscription `cancelled`, records `cancelled_at`, but notes access remains until `expires_at` in `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/webhooks.py`.
- Backend already sends immediate cancellation email via `EmailService.send_cancellation_email`.
- Lifecycle email cron code exists, but user confirmed infra has disabled it and it is expected to be removed. Do not build this campaign on that cron.
- Notification messages already contain EN/VI trial-expiry service copy and no price.

## Mobile Evidence

- Mobile `NotificationType.trialExpiry` exists and notification tap routes to `AppConstants.subscriptionTrialExpiryRoute`.
- `AppConstants.subscriptionTrialExpiryRoute` is `/subscription-required?source=trial_expiry`.
- Paywall price-test flag supports payload `{ "offering_id": "...", "discount_offering_id": "..." }`.
- Discount offer UI uses RevenueCat `StoreProduct.priceString`, so storefront-localized prices are already the display path.
- `PaywallEntryScreen` and paywall screen constructors accept `offeringId`, but the value is currently not used to override `paywallProvider` resolution.

## Reuse First

- Reuse `notifications` queue and unique `(user_id, notification_type, scheduled_date)` dedupe.
- Reuse `PostHogAdapter.capture`.
- Reuse existing paywall offering resolution where possible; add a scoped route override rather than a new paywall implementation.

## Unresolved Questions

- Exact D3 timing: preserve current two-hour pre-charge reminder, or send earlier on local D3 morning.

---
phase: 4
title: "Mobile discounted paywall routing"
status: completed
priority: P1
effort: "0.5-1d"
dependencies: [2]
---

# Phase 4: Mobile discounted paywall routing

## Context Links

- Notification navigation: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/notifications/application/notification_navigation_service.dart`
- Subscription constants: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/core/constants/app_constants.dart`
- Subscription route: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/subscriptions/presentation/router/subscription_routes.dart`
- Paywall entry: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/subscriptions/presentation/screens/paywall_entry_screen.dart`
- Paywall provider: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/subscriptions/application/providers/paywall_provider.dart`
- Price flag provider: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/subscriptions/application/providers/paywall_price_test_provider.dart`
- Discount offering provider: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/subscriptions/application/providers/spin_wheel_discount_offering_provider.dart`

## Overview

Make `source=trial_expiry` open a real discounted RevenueCat offering so the paywall displays localized store prices. This should reuse current offering/purchase UI, not create a second paywall.

## Key Insights

- `trial_expiry` push routing already reaches `/subscription-required?source=trial_expiry`.
- The app already reads `discount_offering_id` from `paywall_price_ab_new_onboarding_v1`.
- `PaywallEntryScreen` and paywall screens accept `offeringId`, but that value is currently not wired into `paywallProvider`.
- Paywall and discount UI already display RevenueCat `priceString`, which solves VN 299k vs other-country price localization.

## Requirements

- Functional: for `source=trial_expiry`, resolve a trial-end discount offering and show that offering in the paywall.
- Functional: use `discount_offering_id` from PostHog payload when present; fallback to the configured standard discount offering.
- Functional: if discount offering/product is missing, fail safe to current paywall instead of blank UI.
- Non-functional: no hardcoded currency/price strings; no new paywall surface unless current UI cannot support the offer.

## Architecture

Notification tap -> route `source=trial_expiry` -> resolve discount offering ID -> scoped paywall offering override -> `paywallProvider` loads `offerings.all[override]` -> UI renders localized product prices.

Preferred mobile implementation:

- Add a small route-scoped provider for paywall offering override.
- `paywallProvider` selection priority:
  1. route override offering ID
  2. price-test `offering_id`
  3. NM-127/tiered/current offering fallback
- `PaywallEntryScreen` passes source and offering override into the paywall via `ProviderScope` or equivalent Riverpod scoped override.

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/subscriptions/application/providers/paywall_provider.dart`
- Create/Modify: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/subscriptions/application/providers/paywall_route_offering_provider.dart`
- Modify: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/subscriptions/presentation/router/subscription_routes.dart`
- Modify: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/subscriptions/presentation/screens/paywall_entry_screen.dart`
- Modify: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/subscriptions/presentation/screens/multi_step_paywall_screen.dart`
- Modify: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/docs/paywall-price-ab-testing.md`
- Modify/Add tests near existing subscription provider/widget tests.

## Implementation Steps

1. Add `paywallRouteOfferingProvider` with default `null`.
2. Update `paywallProvider` to read route override before PostHog price-test offering.
3. In `subscription_routes.dart` or `PaywallEntryScreen`, when source is `trial_expiry`, resolve:
   - `(await paywallPriceTestAssignmentProvider.future).discountOfferingId`
   - fallback `spinWheelDiscountOfferingProvider.future`
   - fallback current paywall if still null
4. Pass the resolved offering into a scoped override around `MultiStepPaywallScreen`.
5. Ensure analytics still reports `offering_id` via `paywall_variant_resolved`.
6. Add tests for route source, offering resolution, missing offering fallback, and localized price display via `StoreProduct.priceString`.
7. Run `dart run build_runner build --delete-conflicting-outputs` if provider code-gen changes.

## Todo List

- [x] Add route-scoped offering override provider.
- [x] Wire override into `paywallProvider`.
- [x] Resolve trial-expiry discount offering from current flag payload.
- [x] Add tests and regenerate Riverpod code.
- [x] Update paywall price-test docs.

## Success Criteria

- [x] Tapping a trial-expiry push opens paywall with the discount offering when configured.
- [x] VN users see the RevenueCat/App Store localized VND price; other countries see their local price.
- [x] Missing discount offering falls back gracefully.
- [x] No user-facing string says `299k` unless it comes from store product price display.

## Risk Assessment

- Risk: scoped override leaks to later paywall opens. Mitigation: use route-scoped provider override, not global state.
- Risk: price-test flag payload missing `discount_offering_id`. Mitigation: fallback to existing discount offering and log diagnostic analytics.
- Risk: generated Riverpod files drift. Mitigation: run build_runner and targeted tests.

## Security Considerations

- Do not include user identifiers in route query params.
- Do not trust route params for entitlement. RevenueCat purchase/entitlement still decides access.

## Next Steps

Phase 5 verifies analytics, docs, and rollout safety.

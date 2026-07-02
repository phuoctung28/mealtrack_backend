---
title: "RevenueCat and PostHog Workflow Research"
type: research
status: complete
created: 2026-07-02
---

# RevenueCat and PostHog Workflow Research

## Summary

PostHog Workflow is feasible for winback email after cancellation if the person has an email property and the email channel is verified. It should not be the mobile push owner. Backend FCM remains the correct push path.

## Findings

- PostHog Workflows can trigger from events, delay, branch, and send email through configured channels.
- PostHog email requires channel/domain setup before launch.
- PostHog push notification support is not the reliable implementation path for this app now; backend FCM already exists.
- RevenueCat webhooks provide lifecycle events that backend already mirrors into PostHog as `subscription_cancelled`, `subscription_expired`, `subscription_renewed`, and related actions.
- Do not assume RevenueCat webhook includes `offering_id`. Verify sandbox payload before using any offer-specific field. Product IDs and discount identifiers are safer claim signals.
- Apple guideline 4.5.4 allows promotional/direct marketing push only with explicit consent and in-app opt-out. Keep the D3 push as a service reminder and put price/discount on paywall/email surfaces.

## Recommended Contract

- Push: backend FCM, service reminder, no hardcoded price.
- Paywall: mobile opens RevenueCat discount offering and renders `priceString`.
- Claim: backend marks offer claimed only from RevenueCat-confirmed discounted product/discount identifier.
- Email: choose one owner. If PostHog owns cancellation winback, disable/gate backend immediate cancellation email for that audience.

## References

- https://posthog.com/docs/workflows
- https://posthog.com/docs/workflows/configure-channels
- https://posthog.com/docs/workflows/launch-workflow
- https://www.revenuecat.com/docs/integrations/webhooks/event-types-and-fields
- https://developer.apple.com/app-store/review/guidelines/

## Unresolved Questions

- Confirm exact RevenueCat sandbox payload fields for discounted purchase before coding the final claim detector.

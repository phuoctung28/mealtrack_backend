---
phase: 2
title: "Harden Entitlement and Concurrency"
status: in_progress
priority: P1
effort: "6-8h"
dependencies: [1]
---

# Phase 2: Harden Entitlement and Concurrency

## Overview

Close the correctness gaps between PayPal approval, webhook delivery, claims,
and premium access. The result is a provider-neutral web entitlement that
coexists with RevenueCat without changing native billing behavior.

## Requirements

- PayPal browser `onApprove` binds a subscription reference only; it never
  changes paid or premium state.
- A verified PayPal payment event plus a fetched subscription snapshot is the
  only paid transition. Revoke on cancellation, suspension, refund, or dispute.
- Concurrent requests and duplicate events must resolve through database
  uniqueness, not a read-then-insert race.
- A valid one-time claim must become visible to `require_subscription`; existing
  RevenueCat verification remains the fallback for native users.

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/services/web_funnel_checkout_service.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/services/paypal_webhook_service.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/repositories/web_funnel_checkout_repository.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/adapters/paypal_billing_adapter.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/web_funnel.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/webhooks.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/middleware/premium_check.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/repositories/subscription_repository_async.py`
- Create: forward-only migration only if constraints/indexes need correction
- Create: route, repository-concurrency, adapter, webhook, claim, and premium tests

## Implementation Steps

1. Move outbound PayPal calls outside database write transactions. Re-open a
   short transaction to conditionally bind the verified result, then handle
   uniqueness conflicts as idempotent outcomes.
2. Use `INSERT ... ON CONFLICT` or a caught database uniqueness error for lead,
   checkout, event, and claim paths. Test two concurrent identical checkout
   requests, two confirmations, two claims, and duplicate webhook deliveries.
3. Fix webhook-before-confirmation ordering. Persist verified unmatched events
   for reconciliation or let confirmation safely retrieve and apply the latest
   verified PayPal state; do not permanently discard a valid early event as
   `checkout_not_found`.
4. Treat a fetched subscription as valid only when plan, signed `custom_id`,
   merchant when configured, amount, currency, and expected paid lifecycle all
   match. Keep unknown/malformed events non-entitling and observable.
5. Add the local claimed web subscription to premium resolution with a database
   lookup that checks provider, status, and expiry. Preserve current RevenueCat
   semantics and add regression tests for native users.
6. Replace float-based money parsing in the adapter with decimal minor-unit
   conversion; record provider payment/customer identifiers where present.

## Success Criteria

- [x] Approval, invalid signature, wrong plan, wrong merchant, amount/currency
  mismatch, replay, and early webhook cannot grant a false entitlement.
- [x] A valid verified payment can be claimed once, grants premium, and a later
  revoke removes premium without affecting RevenueCat subscriptions.
- [ ] Concurrent paths preserve one ledger row/event/claim without 500 errors.
- [x] No outbound PayPal HTTP request runs while a database transaction is open.

## Progress Notes

- 2026-07-26: Browser approval binds the PayPal subscription only; claim token
  is returned only from paid/claimable status.
- 2026-07-26: PayPal sale webhooks now correlate through `billing_agreement_id`
  and early verified events are stored for later reconciliation.
- 2026-07-26: Repository paths now catch duplicate lead/checkout/event conflicts,
  map duplicate confirmation to typed conflict, and lock claim before consuming.
- 2026-07-26: Focused unit tests cover the above behavior. Real PostgreSQL
  concurrency proof remains open for Phase 3 local sandbox acceptance.

## Risk Assessment

This is the high-risk phase. Do not substitute unit mocks for the PostgreSQL
concurrency cases; run them against the local database used for sandbox.

---
title: "PayPal Web Funnel Release Plan"
description: "Finish the backend-owned PayPal funnel, prove it in sandbox, and enable it safely for international production traffic."
status: in_progress
priority: P1
effort: "2-3d"
branch: "delivery"
tags: [feature, backend, frontend, api, database, payments, critical]
blockedBy: []
blocks: []
created: "2026-07-26"
---

# PayPal Web Funnel Release Plan

## Outcome

Ship PayPal subscriptions for non-Vietnam (`INTL`) funnel traffic only. The
browser creates a PayPal subscription with a server-selected plan; the backend
grants premium only after a verified PayPal payment event and an authenticated
claim. Vietnam stays unavailable until its separate MoMo implementation exists.

## Verified Starting Point

| Area | Current state | Release decision |
|---|---|---|
| Ledger, PayPal REST adapter, webhook route | Implemented locally | Keep; harden races and lifecycle recovery |
| Browser approval | Posts `subscriptionID` and polls status | Keep pending; never grant from approval |
| Funnel prerequisites | Calls missing lead/context/reward endpoints | Reconcile one contract before sandbox |
| Premium gate | Still follows legacy local/RevenueCat logic | Add claimed PayPal subscription support |
| Idempotency and webhook dedupe | Read-then-insert | Make database-conflict-safe |
| Local DB | Migrated through `20260726000003` | Use sandbox only after final test gates |

## Architecture

```text
Funnel lead/context -> backend contract -> server-owned offer snapshot
PayPal JS SDK -> subscriptionID -> confirmation (pending only)
PayPal webhook -> signature verification -> fetch subscription -> paid_active
Firebase-authenticated app -> one-time claim -> active local web subscription
Premium middleware -> active web subscription or existing RevenueCat path
```

PayPal's subscription integration uses the JavaScript SDK with
`vault=true&intent=subscription` and a pre-created plan. Its documented webhook
verification endpoint is the authority for webhook sender validation. See
[PayPal subscriptions](https://developer.paypal.com/docs/subscriptions/integrate/)
and [webhook verification](https://developer.paypal.com/docs/api/webhooks/v1/).

## Phases

| Phase | Name | Status |
|---|---|---|
| 1 | [Align Funnel and API Contracts](./phase-01-web-funnel-checkout-foundation.md) | Complete |
| 2 | [Harden Entitlement and Concurrency](./phase-02-paypal-checkout-and-confirmation.md) | In Progress |
| 3 | [Run Local Sandbox Acceptance](./phase-03-verified-entitlement-and-claim.md) | Pending |
| 4 | [Deploy and Observe Production](./phase-04-tests-and-production-rollout.md) | Pending |

## Non-Negotiable Release Gates

- No `WEB_FUNNEL_CHECKOUT_ENABLED=true` in production until every Phase 3 case passes.
- Production and sandbox use separate PayPal client credentials, plan IDs, and
  webhook IDs. The client secret is backend-only and must be rotated because it
  was pasted into this conversation.
- The funnel's `NEXT_PUBLIC_PAYPAL_CLIENT_ID` must be the public client ID for
  the same merchant that owns the configured plan IDs.
- `WEB_FUNNEL_PAYPAL_OFFERS_JSON` remains a server-owned catalog mapping offer
  IDs to PayPal plan IDs, prices, currency, reward, and renewal terms. The
  browser never supplies any of those commercial fields.
- Do not route `VN` to PayPal/USD. Return the existing unavailable response
  until MoMo is implemented and separately verified.

## Environment Inputs

Backend, sandbox then production: `WEB_FUNNEL_CHECKOUT_ENABLED`,
`WEB_FUNNEL_SIGNING_SECRET`, `WEB_FUNNEL_CLAIM_TOKEN_TTL_MINUTES`,
`WEB_FUNNEL_PAYPAL_OFFERS_JSON`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`,
`PAYPAL_API_BASE_URL`, `PAYPAL_WEBHOOK_ID`, optional `PAYPAL_MERCHANT_ID`, and
`PAYPAL_TIMEOUT_SECONDS`. The funnel needs only `NEXT_PUBLIC_API_BASE_URL` and
`NEXT_PUBLIC_PAYPAL_CLIENT_ID`.

## Rollback

Disable `WEB_FUNNEL_CHECKOUT_ENABLED` to stop new checkout creation. Keep the
PayPal webhook endpoint and existing offer mapping alive long enough to settle
already-created subscriptions, claims, cancellations, refunds, and disputes.
Do not roll back the database migrations or alter the RevenueCat flow.

## Exit Criteria

- The real funnel reaches checkout without a missing endpoint or contract fallback.
- A sandbox approval remains pending until a verified payment event; one valid
  claim grants premium, while replay, mismatch, cancellation, and refund do not.
- Migration, route, service, repository, adapter, frontend unit, lint, and
  production-build gates pass.
- Production has the exact HTTPS webhook URL, subscribed events, secret store
  configuration, dashboard alerting, rollback owner, and first-hour monitor.

## Unresolved Questions

- None for the PayPal-only international release. MoMo remains explicitly out
  of scope and fail-closed for Vietnam.

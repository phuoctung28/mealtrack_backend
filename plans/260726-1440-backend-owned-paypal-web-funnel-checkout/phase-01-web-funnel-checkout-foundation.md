---
phase: 1
title: "Align Funnel and API Contracts"
status: complete
priority: P1
effort: "4-6h"
dependencies: []
---

# Phase 1: Align Funnel and API Contracts

## Overview

Make the deployed funnel and backend agree on one public contract before any
PayPal button can be used. This eliminates the current missing
`/v1/web-funnel/leads`, `/api/funnel/context`, and welcome-reward endpoints
from the payment path.

## Requirements

- Keep the existing 23-step funnel and its country rule: `VN -> MoMo/VND`, all
  non-VN markets -> PayPal/USD.
- Choose one source of truth for lead identity, country/context, `WELCOME50`,
  and the server-selected offer. Do not preserve unused legacy endpoints merely
  because the frontend calls them today.
- The checkout response must retain the camelCase shape consumed by the PayPal
  component without exposing secrets or mutable commercial values.

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/nutree_web_funnel/src/lib/api/client.ts`
- Modify: `/Users/alexnguyen/Desktop/Nut/nutree_web_funnel/src/app/email/page.tsx`
- Modify: `/Users/alexnguyen/Desktop/Nut/nutree_web_funnel/src/app/paywall/page.tsx`
- Modify: `/Users/alexnguyen/Desktop/Nut/nutree_web_funnel/src/app/welcome-gift/page.tsx`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/web_funnel.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/schemas/request/web_funnel_requests.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/schemas/response/web_funnel_responses.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/services/web_funnel_checkout_service.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/app/services/test_web_funnel_checkout_service.py`
- Create: focused route/client contract tests in the existing unit-test layouts

## Implementation Steps

1. Write a one-page contract table for `lead`, `context/reward`, `checkout`,
   `confirmation`, `status`, and `claim`, including request field casing and
   error codes. Treat it as the implementation checklist for both repositories.
2. Remove or replace the frontend calls that target backend routes which do not
   exist. Prefer the smallest compatible path: a browser-generated opaque lead
   ID accepted by checkout, and a backend response/catalog that is actually
   served by the backend. Do not add an unauthenticated email/profile store just
   to mimic an obsolete response.
3. Make country selection authoritative at the backend boundary. Non-VN must
   select only a configured USD PayPal offer; VN must return the typed
   unavailable state until MoMo work is approved.
4. Preserve backend ownership of offer, reward, plan, amount, currency, and
   renewal data. Validate the offer catalog at startup with actionable failures
   for malformed JSON, unsupported currency/provider, non-positive amount, or
   missing plan ID.
5. Confirm claim-token handoff is intentional: keep it opaque, never log it,
   never put it in analytics, and do not issue an entitlement before Firebase
   authentication.

## Success Criteria

- [x] Email, welcome-gift, paywall, checkout, and success screens make no call
  to a missing backend route.
- [x] Frontend and backend contract tests prove aliases, error codes, country,
  and provider selection.
- [x] Bad offer configuration prevents checkout service startup/enablement.

## Progress Notes

- 2026-07-26: Removed runtime calls to missing lead, context, and reward routes
  in `nutree_web_funnel`; checkout is now the first backend payment boundary.
- 2026-07-26: Aligned frontend reward payload to backend `WELCOME50`, retained
  backend-owned PayPal/USD selection for non-VN, and kept VN fail-closed.
- 2026-07-26: Checkout response now carries backend commercial display fields
  and no pre-paid claim token.

## Risk Assessment

The main risk is accidentally restoring old MoMo assumptions while shipping
PayPal. Keep the release INTL-only and fail closed for VN.

---
phase: 4
title: "Deploy and Observe Production"
status: pending
priority: P1
effort: "3-4h"
dependencies: [1, 2, 3]
---

# Phase 4: Deploy and Observe Production

## Overview

Deploy the tested code and forward migrations, wire the production PayPal
webhook, then enable international checkout in a controlled, reversible step.

## Requirements

- Deploy migrations before enabling `WEB_FUNNEL_CHECKOUT_ENABLED`.
- Use production PayPal client credentials, production plan IDs, production
  webhook ID, production API base URL, and an independently generated signing
  secret.
- Keep `VN` unavailable. Keep existing RevenueCat webhook and mobile purchase
  flows unchanged.

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/api-endpoints.md`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/external-services.md`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/project-changelog.md` when release is complete
- Modify: deployment secret store and PayPal dashboard outside git

## Implementation Steps

1. Create/verify the production webhook at
   `https://<backend-host>/v1/webhooks/paypal`. Subscribe to payment-completed,
   cancellation, suspension, refund, and dispute events used by the lifecycle
   mapping. Copy its production webhook ID into the secret store.
2. Deploy the backend with checkout disabled. Run migrations, `/health`,
   `/openapi.json`, route availability, CORS preflight from the deployed funnel
   domain, and a disabled-checkout smoke test.
3. Deploy the funnel with production `NEXT_PUBLIC_API_BASE_URL` and the public
   client ID matching the production plans. Verify page load and provider
   choice without exposing the secret.
4. Enable checkout for a restricted international canary. Monitor checkout
   create/confirmation/pending/paid/claim/revoke counts; PayPal signature
   failures; mismatch reasons; webhook latency; 4xx/5xx; and premium failures.
5. Execute one controlled production purchase only if business policy permits;
   otherwise validate webhooks with PayPal's production simulator and defer the
   first buyer observation to support monitoring. Document the chosen evidence.
6. Roll back by disabling new checkout creation on any signature, mismatch,
   claim, or premium regression. Continue webhook/reconciliation processing for
   existing purchases until all pending ledger rows are resolved.

## Success Criteria

- [ ] Deployed OpenAPI exposes the exact checkout, confirmation, status, claim,
  and PayPal webhook routes.
- [ ] Production webhook verification succeeds and observability can distinguish
  pending, paid, claimed, revoked, ignored, and failed events.
- [ ] International checkout is enabled only after the canary is healthy; VN and
  native RevenueCat behavior remain unchanged.
- [ ] Rollback owner and procedure are written in the deployment record.

## Risk Assessment

Most production failures will be configuration mismatches: wrong environment,
wrong plan owner, wrong webhook ID, or CORS origin. Treat each as a stop signal,
not a reason to weaken signature checks or bypass the backend ledger.

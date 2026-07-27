---
phase: 3
title: "Run Local Sandbox Acceptance"
status: pending
priority: P1
effort: "4-6h"
dependencies: [1, 2]
---

# Phase 3: Run Local Sandbox Acceptance

## Overview

Prove the real PayPal sandbox lifecycle against the local migrated PostgreSQL
database and the local funnel. This phase is the final technical go/no-go for
production configuration.

## Requirements

- Use local backend at `http://127.0.0.1:8000`, local funnel at
  `http://localhost:3000`, and a publicly reachable HTTPS tunnel only for the
  sandbox webhook callback.
- Use sandbox client credentials, sandbox plan IDs, sandbox webhook ID, and a
  sandbox buyer. Do not reuse production credentials or plans.
- Record redacted evidence only: checkout ID, timestamps, HTTP statuses,
  state transitions, and PayPal dashboard references. Never store secrets,
  tokens, or full buyer details in the repository.

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/.env` locally only
- Modify: `/Users/alexnguyen/Desktop/Nut/nutree_web_funnel/.env.local` locally only
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/integration/test_web_funnel_checkout_repository.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/migrations/test_web_funnel_billing_migrations.py`
- Modify: existing focused backend and funnel unit tests

## Implementation Steps

1. Run Alembic against a clean local PostgreSQL database, then run the upgrade
   path from the previous deployed revision. Verify the head is
   `20260726000003` or its approved forward successor.
2. Start the backend with local database, exact localhost CORS origins,
   checkout enabled, sandbox API base URL, sandbox offer catalog, and unique
   signing secret. Start the funnel with the paired local API URL and sandbox
   public client ID.
3. Confirm the health endpoint, CORS preflight, OpenAPI routes, malformed
   checkout errors, non-VN checkout creation, and VN unavailable response.
4. Complete the real buyer flow: lead/context -> checkout -> PayPal approval ->
   confirmation -> pending status -> webhook -> paid/claimable -> Firebase
   authenticated claim -> premium-protected endpoint.
5. Run negative cases: approval without webhook, invalid signature, duplicate
   event, repeated confirmation, early webhook, bad subscription reference,
   cancellation/refund, repeated claim, expired claim, and a native RevenueCat
   regression case.
6. Run focused backend lint/compile/tests, PostgreSQL integration/migration
   tests, and funnel `eslint`, `npm test`, and `npm run build`. Do not add or
   run browser e2e tests in `nutree_web_funnel`.

## Success Criteria

- [ ] One real sandbox payment reaches premium only after verified webhook and
  authenticated claim.
- [ ] Every negative case fails closed and leaves a support-traceable state.
- [ ] Local migration, focused backend tests, funnel lint/unit/build, and CORS
  checks pass with no dependency on production infrastructure.

## Risk Assessment

PayPal cannot deliver a webhook directly to loopback. The tunnel is sandbox
test infrastructure only; production must point to the deployed HTTPS URL and
use a separate webhook ID.

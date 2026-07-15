---
title: "Reliable Write Contract Backend"
description: "Add fail-closed, capability-gated idempotency and reconciliation for critical meal, weight, onboarding, promo, and referral writes."
status: in-progress
priority: P1
branch: "main"
tags: [backend, api, database, reliability, critical]
blockedBy: []
blocks: []
created: "2026-07-14T08:12:00.825Z"
updated: "2026-07-15"
createdBy: "ck:plan"
source: skill
---

# Reliable Write Contract Backend

## Overview

Build a reusable reliable-write contract without changing legacy client behavior.
Operation-aware requests use UUIDv4 identity, canonical fingerprints, durable
user/action-scoped results, reconciliation lookup, and remote kill switches.
Requests without the contract keep current behavior; every new capability ships
disabled until its integration and compatibility gates pass.

This backend plan unblocks mobile Phase 4 and the purchase-finalization slices of
Phase 5 in `../mobile/plans/260714-0918-reliability-architecture-remediation/`.
Phase 0 authority and redaction implementation has started. No reliable-write
migration, API, or capability enablement has started.

## Readiness Status — 2026-07-15

- Final foundation review: **rejected**. Phase 1 and Phase 2 must not start or
  deploy until the open canonical-input, legacy-weight-compatibility, and Phase 0
  redaction gates below pass renewed review.
- Phase 0: in progress. PostgreSQL/CQRS authority, strict `postgres` marker, and
  migration-marker paths are resolved. Generic path telemetry and the missing
  exception/provider/SQL sentinel suites remain open.
- Resolved design gates: all capability rows default false with
  `ever_enabled=false`; v1 has no cohort/allowlist; any first enablement is a
  separately approved global enablement for one action.
- Open canonical declarations: manual item `fdc_id`/`name` and resolved
  `Accept-Language`; suggestion top-level protein/carbs/fat; URL scan mode
  `scanner` normalization and cross-repo changed-field fixtures.
- Open weight storage policy: the expand migration must preserve every current
  legacy positive-float write, including values above 999.999 and below 0.001.

## Contract Direction

- Header and body must contain the same canonical UUIDv4; partial, invalid, or
  mismatched identity fails before mutation.
- Database uniqueness: `(authenticated_user_id, action, client_operation_id)`.
- Same key + same RFC 8785/JCS v1 fingerprint replays the exact stored v1 HTTP
  status and logical JSON body; different fingerprint returns
  `409 IDEMPOTENCY_KEY_REUSED`.
- A durable pending reservation may precede external scan work, but the domain
  mutation, exact response snapshot, and required effect/outbox rows are written
  in one transaction.
- `GET /v1/write-capabilities` is authenticated, versioned, TTL-bound, and
  fail-closed. A dedicated capability table/cache (maximum 30-second process
  TTL) is the remote kill switch; it never reuses the existing 600-second
  feature-flag cache.
- `GET /v1/write-operations/{action}/{client_operation_id}` is authenticated and
  remains available while writes are disabled and returns
  `pending|committed|notFound|expired|permanentFailure`.
- Stable actions include `meal.suggestion.create`; every action flag is false.
  V1 has no cohort targeting: first enablement, if separately approved, is global
  for that action in production. Until then production cohort is none.
- Backend-calculated calories remain derived from macros using
  `P*4 + (C-fiber)*4 + fiber*2 + F*9`.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 0 | [Authority and Pre-route Redaction](./phase-00-authority-and-pre-route-redaction.md) | In Progress |
| 1 | [Contract and Migration Foundation](./phase-01-contract-and-migration-foundation.md) | Blocked |
| 2 | [Capability and Reconciliation API](./phase-02-capability-and-reconciliation-api.md) | Blocked |
| 3 | [Meal Write Integration](./phase-03-meal-write-integration.md) | Pending |
| 4 | [Weight Write Integration](./phase-04-weight-write-integration.md) | Pending |
| 5 | [Onboarding Promo and Referral Decisions](./phase-05-onboarding-promo-and-referral-decisions.md) | Pending |
| 6 | [Compatibility Observability and Rollout](./phase-06-compatibility-observability-and-rollout.md) | Pending |

## Dependencies

- Hard consumer dependency: mobile reliable-write decision record and endpoint
  inventory under `../mobile/`; backend lands before mobile enables replay.
- Related, not blocking: pending `260612-1046-service-initiated-bandwidth-reduction`
  touches scan-by-URL upload flow; coordinate file ownership during implementation.
- Current Alembic head verified as `20260702000001`; implementation must re-check.
- Product/mobile/release gates remain explicit in Phase 6. All capability rows
  default false; v1 has no cohort columns or per-user admission behavior.
- Hard implementation gate: do not create or deploy reliable-write migrations,
  manifest/lookup APIs, or operation-aware routes until Phase 0 is complete and
  a renewed foundation review approves the corrected Phase 1 contract.

## Delivery Gates

1. Instruction-authority correction and telemetry/Sentry/SQL redaction tests.
2. PostgreSQL expand migrations (reliable-write foundation and weight NUMERIC),
   foundation, manifest, and lookup with all actions
   false; lookup is never capability-gated.
3. Meal, durable-effect, and exact-response replay tests.
4. Partial weight batch and purchase-finalization convergence tests.
5. Shared cross-repo fixtures, old/new staging matrix, fault injection, and only
   then separately approved per-action global rollout. Cohort/allowlist rollout
   requires a future migration, manifest contract, deterministic assignment, and
   admission tests.

## Prioritized Next Steps

1. Finish Phase 0: remove generic path telemetry or accept only a trusted
   FastAPI route template, then add and pass exception-handler,
   provider-observability, and real-PostgreSQL SQL sentinel tests.
2. Complete the exhaustive fingerprint inventory and paired Python/Dart fixture
   declarations for manual, suggestion, and URL-scanner inputs.
3. Validate the unbounded nullable NUMERIC compatibility policy against all
   current legacy positive-float writes while keeping operation-aware validation
   isolated behind disabled capabilities.
4. Rerun strict plan validation and independent foundation readiness review.
5. Only after approval, implement the disabled Phase 1 foundation and Phase 2
   manifest/lookup. Do not deploy or enable any reliable-write capability as part
   of that approval.

## Global Success Criteria

- One accepted operation creates at most one canonical entity/effect.
- Timeout-after-commit reconciles without blind replay.
- Old clients keep existing request/response compatibility.
- New clients treat missing, stale, disabled, or unknown capability data as no-retry.
- Logs/metrics exclude UID, operation ID, fingerprint, bodies, meal/image/weight
  values, promo/referral codes, tokens, URLs, and credentials.
- Shared versioned backend/mobile fixtures pin canonicalization, manifest,
  lookup, replay, weight, benefit, and UTC behavior before either client enables.

## Blocking Approvals (Defaults Applied)

The design choices are selected in this plan so implementation is deterministic,
but capability enablement remains blocked on: mobile acceptance of exact logical
JSON replay v1; product/mobile acceptance of operation-aware same-instant weight
upsert and partial-batch outcomes; product acceptance of onboarding/promo/referral
duplicate semantics and immutable one-benefit referral attribution; a named
release owner/pause authority; numeric rollout thresholds and minimum observation
volume. The fail-closed defaults are all action rows false, no production
enablement, no automatic retry, and lookup-only reconciliation.

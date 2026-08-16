---
phase: 4
title: "Make Create And Edit Reference Authoritative"
status: completed
effort: 4.5d
---

# Phase 4: Make Create And Edit Reference Authoritative

## Context Links

- [Backend persistence research](./research/backend-contract-and-persistence.md)
- `src/api/schemas/request/meal_requests.py`
- `src/api/routes/v1/meals_manual_text.py`
- `src/api/routes/v1/meals_edit.py`
- create/edit command handlers and edit strategies
- `src/infra/database/models/nutrition/food_item.py`
- `src/api/routes/v1/meals_read.py`
- existing meal-recommendation idempotency pattern

## Overview

Priority P1. Resolve preview/create/edit through one server-side service, persist immutable source snapshots, and make retries durable. Client nutrition and serving conversions never override a reference. Explicit user overrides remain a separate audited exception.

## Key Insights

- Current create trusts client custom nutrition; edit prioritizes it and can persist zero fallback.
- Edit remove/quantity-only actions legitimately carry no new food origin.
- Item and meal `nutrition_override` can bypass source calories unless explicit intent is separated from generated client data.
- Flutter already sends `Idempotency-Key` only when `/v1/capabilities/durable-writes` advertises support; backend currently provides neither contract.
- Provider resolution before ownership or without commit-time eligibility checks creates authorization and quarantine races.

## Requirements And Architecture

### Version And Action Matrix

- Both version and origin absent: legacy field inference, strict validation, attempt/success/failure metrics.
- V2 sends `X-Nutrition-Contract-Version: 2`, `X-App-Version`, and `X-Platform`; contract header must match body version. Origin without version, mismatch, or unknown version -> 422.
- V2 create/add/source replacement: `origin=local|usda|provider` requires exactly its matching source identifier and prohibits other IDs; `origin=custom` requires validated custom nutrition and prohibits every reference ID. Zero/multiple/mismatching fields -> 422.
- V2 quantity/unit update: owned item ID only, inherit immutable source snapshot, reject a conflicting supplied source; resolve units from the snapshot.
- V2 item override update: owned item ID, `override_intent=user_entered`, and bounded absolute values; retain source snapshot and reject a replacement origin in the same change. Meal-level override uses the same v2 intent without an item origin.
- V2 remove: owned item ID only; reject source, nutrition, override, quantity, or serving fields.
- V2 clear-override: owned item ID plus explicit clear intent; restore the immutable source snapshot.
- Reference plus custom macros: ignore and meter custom macros for legacy compatibility; v2 rejects the conflicting field.

### Overrides

- Preserve item/meal `nutrition_override` only with an explicit `override_intent=user_entered` discriminator from deliberate UI. Source identity/snapshot remains stored for reset.
- Backend validates finite, nonnegative, domain-bounded absolute calories/macros and records override state separately. Overrides need not match the macro formula because they are the documented exception.
- V2 rejects an override without explicit intent. Flutter/parser/barcode code may never synthesize an override from macros or provider values.

### Resolution, Authorization, And Resources

- Cap requests at 50 items; deduplicate/batch canonical and USDA reads.
- Edit performs a short permission/version preflight before external I/O, resolves outside a DB write transaction, then locks/reloads the meal and rechecks owner/version inside the write UoW.
- Commit-time local-reference check locks or digest-revalidates eligibility/policy version; concurrent quarantine or source correction aborts persistence. Unauthorized/rate-rejected requests make zero provider calls.
- Referenced units come only from backend snapshots. Client `allowed_units`/gram weights are ignored; unsupported units fail closed.
- Apply authenticated per-user limits to preview/create/edit. Provider work uses a shared distributed budget plus a bounded per-process semaphore and bounded single-flight keyed by namespace/ID. If shared limiting is unavailable, arbitrary provider-ID resolution fails closed while local/custom paths continue.
- Initial safety defaults: preview 20/user/minute, create/edit 10/user/minute, at most 20 unique external IDs/request, provider concurrency 4/request and 8/process, 5-second request-wide provider deadline, and single-flight capped at 256 keys/30 seconds. Distributed global RPM is a required production value not exceeding the contracted provider quota; missing shared budget fails external-ID resolution closed. All settings have boundary tests—no unbounded memory cache.

### Persistence, Reads, And Idempotency

- Mandatory food-item migration stores nullable legacy-compatible `source_kind`, provider `source_food_id`, `nutrition_contract_version`, and immutable source snapshot containing basis, per-100g macros, backend-derived calories, and serving conversions.
- V2 success contains authoritative `meal_detail`; reads use snapshots and batch-load only legacy references.
- Add a durable user-scoped write-operation table keyed by user, operation, and `Idempotency-Key`, with canonical request fingerprint, lease/status, target meal, and replayable authoritative response.
- V2 create/edit require valid idempotency keys. Identical replay returns the original response; same key/different fingerprint returns `idempotency_conflict` 409; concurrent keys produce one committed mutation; stale pending leases recover safely.
- Pending lease is bounded and recoverable with a monotonically increasing fencing generation plus unguessable lease-owner token. Final mutation/completion atomically checks both, so an expired worker cannot commit after takeover. Completed replay records retain 30 days with indexed bounded-batch cleanup; cleanup never removes an active lease or the only recovery record inside the supported offline retry window.
- Sequence: validate/rate/authorize, reserve or replay the idempotency operation in a short transaction, resolve externally under its lease, then commit meal mutation plus completed response atomically. Retryable pre-commit failure releases/expires the lease for the same key.
- Advertise manual create/edit support from `/v1/capabilities/durable-writes` only after migration and replay service are live.

### Errors And Observability

- Stable errors: invalid origin/override/ineligible/integrity -> 422; idempotency mismatch -> 409; rate limit -> 429; transient provider -> 503 with `Retry-After`.
- A route-scoped pre-Pydantic wrapper counts every authenticated create/edit attempt—including schema-rejected 4xx—using contract/app/platform headers only, then records response class. Allowlisted resolver fields/enums are contract version, action, authority path, result, and reason code; never item text, request payload, raw IDs, command objects, or PII.

## Related Code Files

Modify:

- request/response schemas, manual-create/edit/read routes, mappers, commands, handlers
- nutrition/food-item-change domain models and edit strategies
- food-reference eligibility/batch ports and repositories
- food-item ORM, meal repository, dependencies/event bus
- rate-limit and observability connectors/tests
- Flutter-compatible capabilities route registration

Create:

- shared manual-item resolution/preview application service
- provider resolution coordinator with bounded distributed budget/single-flight
- durable meal-write idempotency model/port/repository/service
- mandatory snapshot/idempotency migration and migration tests
- create/edit/read/preview/idempotency integration contracts

## TDD Implementation Steps

1. Add action-aware legacy/v2 header/body matrix, override-intent, alias, provider-ID, 50-item, pre-validation telemetry, and stable-error tests.
2. Add resolver tests for all origins, eligibility, malicious units, custom preview, explicit override/reset, and provider outage.
3. Add authorization/race tests: unauthorized edit makes zero provider calls; edit owner/version is rechecked; concurrent quarantine/correction blocks stale persistence.
4. Add rate/budget tests across users and concurrent requests, including bounded single-flight and limiter-unavailable fail-closed behavior.
5. Add idempotency migration/service tests for replay, fingerprint conflict, concurrent same key, response loss after commit, stale lease takeover, old-owner fenced commit rejection, cleanup boundaries, and capability advertisement.
6. Add equivalent preview/create/edit/read tests for immutable snapshots, v2 authoritative detail, quantity-only inheritance, remove, and override behavior.
7. Reserve/replay idempotency after permission/rate preflight; resolve references outside write UoWs under the lease; lock/revalidate and persist mutation plus completed response atomically.
8. Replace payload/command logging with safe operation/result metadata and add log-capture privacy tests.

## Verification

- Focused contract, resolver, snapshot, authoritative-response, strategy,
  edit-handler, idempotency, repository, provider-budget, capability, and
  legacy-edit regression suites passed: 109 tests.
- CI-aligned unit gate passed: `2360 passed, 44 warnings`, 78.83% coverage,
  with the repository's known `tests/unit/cron/test_push_cron.py` exclusion.
- `./.venv/bin/python -m compileall -q src` passed.
- Ruff F-checks for the changed Phase 4 files passed.
- `./.venv/bin/alembic heads` passed and shows the Phase 4 migration head.
  SQL generation was attempted with the project virtualenv but could not
  connect because this checkout has no valid `DATABASE_URL`; no migration was
  applied.
- A broader integration attempt was environment-blocked by missing existing
  test-database columns (`users.revenuecat_customer_id` and
  `nutrition.nutrition_override`), unauthorized dev-user setup, and an
  unrelated missing `authenticated_client` fixture; it is not counted as a
  Phase 4 pass.

## Success Criteria

- [x] Action-aware v2 create/edit uses one resolver without breaking legacy remove/update semantics.
- [x] Referenced paths never persist client macros/gram weights or generated overrides.
- [x] Permission and commit-time eligibility races fail closed before mutation.
- [x] Provider work is rate-limited, globally bounded, and single-flight without unbounded memory.
- [x] Create/edit retries are durable and exactly one mutation is committed per user/operation/key.
- [x] Every v2 item persists an immutable source snapshot and returns authoritative detail.

## Risks, Security, And Rollout Gate

- Risks: provider latency, lease recovery, migration/read compatibility, mixed clients. Mitigate with bounded pre-resolution, database uniqueness, short leases, nullable snapshots, and capability-gated v2 rollout.
- Security: permission before provider I/O, owner recheck at commit, opaque-ID allowlist, no payload logs, no source IDs/PII in telemetry.
- Gate: additive durable backend create/edit/read contract is deployed and observed before Flutter production rollout.

## Unresolved Questions

None. Explicit user overrides remain the documented backend-validated exception; generated client overrides are prohibited.

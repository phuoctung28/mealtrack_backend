---
phase: 2
title: "Capability and Reconciliation API"
status: pending
priority: P1
dependencies: [0, 1]
effort: "2-3 engineering days"
---

# Phase 2: Capability and Reconciliation API

## Overview

Expose authenticated, versioned capability negotiation and operation lookup.
The manifest is a code allowlist gated by the dedicated capability table from
Phase 1. Missing, stale, unknown, or error states disable operation-aware writes;
lookup remains available even when every write is killed.

## Prerequisite Gate — 2026-07-15

**Blocked / do not start or deploy.** Phase 2 begins only after Phase 0 sentinel
completion, corrected Phase 1 canonical/weight contracts, and renewed independent
foundation approval. Approval still seeds every capability false with
`ever_enabled=false`; it does not authorize deployment or enablement.

## API Contract

`GET /v1/write-capabilities` returns:

```json
{
  "manifest_version": 1,
  "generated_at": "...Z",
  "expires_at": "...Z",
  "ttl_seconds": 30,
  "idempotency_retention_seconds": 2592000,
  "actions": [{
    "action": "meal.manual.create",
    "method": "POST",
    "route_template": "/v1/meals/manual",
    "contract_version": 1,
    "enabled": false,
    "operation_id_transport": "header_and_body",
    "lookup_route_template": "/v1/write-operations/{action}/{client_operation_id}"
  }]
}
```

The registry contains a separate entry for `meal.suggestion.create` mapped to
`POST /v1/meal-suggestions/save`. Every registry action has exactly one database
row and every row starts false.

Use `Cache-Control: private, max-age=30` and `Vary: Authorization`. No stale
grace. A dedicated in-process immutable snapshot has a monotonic 30-second hard
TTL and is never backed by `FeatureFlagService` or the existing 600-second cache
(`src/domain/cache/cache_keys.py`). A process may serve an enabled value only
while that snapshot is unexpired; on expiry, DB/cache/read error fails closed as
503/all-disabled. Dedicated admin update code writes `enabled`, permanently ORs
`ever_enabled`, increments revision, and invalidates its local snapshot; other
processes converge within 30 seconds. Cross-process tests use two independent
cache instances and DB time. Capability is checked before reservation, upload,
AI, or other external work. Flag-off is admission-only for a currently live
lease, blocks new reservation/reclaim, and never disables lookup.

`GET /v1/write-operations/{action}/{client_operation_id}` validates allowlisted
action and UUIDv4, scopes by authenticated internal user ID, and returns 200 for
a well-formed lookup:

```json
{
  "action": "weight.sync",
  "client_operation_id": "...",
  "status": "committed",
  "entity_id": null,
  "canonical_date": null,
  "response_contract_version": 1,
  "http_status": 200,
  "response_body": {"results": []},
  "error_code": null,
  "retention_expires_at": "...Z",
  "retry_after_seconds": null
}
```

The lookup HTTP status is 200 for every valid owner-scoped state. `notFound`
never discloses another user's operation and has all response/retention fields
null. `pending` has null response fields and `retry_after_seconds` in `1..30`;
the mutation response is exactly
`{"code":"OPERATION_IN_PROGRESS","status":"pending","retry_after_seconds":n}`
plus matching `Retry-After`. `expired` exposes only status and tombstone expiry.
`committed` returns the frozen response status/body. `permanentFailure` returns
the frozen safe 4xx status/body and allowlisted error code, never raw exception
text. All five shapes are versioned shared fixtures.

Lookup does not consult the capability flag. It validates auth, compiled action,
UUID, and owner, then reads operation state. Tombstone deletion becomes
`notFound`; clients may resend only when their locally persisted creation time is
within the manifest's advertised 30-day idempotency retention. Otherwise they
surface reconciliation-required and do not auto-retry.

## CQRS and Files

| Action | Path | Purpose |
|---|---|---|
| Create | `src/app/queries/reliable_write/get_write_capabilities_query.py` | Manifest query |
| Create | `src/app/queries/reliable_write/get_write_operation_query.py` | Reconciliation query |
| Create | `src/app/handlers/query_handlers/reliable_write/get_write_capabilities_query_handler.py` | Manifest assembly |
| Create | `src/app/handlers/query_handlers/reliable_write/get_write_operation_query_handler.py` | Owner lookup |
| Create | `src/app/services/reliable_write/capability_registry.py` | Allowlist + capability names |
| Create | `src/app/services/reliable_write/capability_snapshot.py` | Dedicated 30s fail-closed cache |
| Create | `src/api/routes/v1/reliable_writes.py` | Authenticated GET routes |
| Create | `src/api/routes/v1/admin_reliable_writes.py` | Authenticated admin kill-switch update |
| Create | `src/api/schemas/response/reliable_write_responses.py` | Versioned responses |
| Modify | `src/api/dependencies/event_bus.py` | Register query handlers |
| Modify | `src/api/main.py` | Register router |
| Create | `tests/unit/app/handlers/query_handlers/reliable_write/test_capabilities.py` | Fail-closed tests |
| Create | `tests/unit/app/handlers/query_handlers/reliable_write/test_operation_lookup.py` | Ownership/status tests |
| Create | `tests/unit/api/test_reliable_write_routes.py` | Auth/schema/cache headers |

## Implementation Steps

1. Write route schema snapshots and unauthenticated 401 tests first.
2. Implement a static action registry including suggestion. Route templates,
   methods, contract versions, lookup path, and capability names never come from
   request data. Add an equality guardrail among registry, migration rows,
   manifest fixtures, lookup allowlist, routes, and integration fixtures.
3. Read only the dedicated capability table in one query. Capability is
   `compiled_support AND database_enabled`; either false disables it. Implement
   the 30-second snapshot and admin revision invalidation without generic flags.
4. Add read-only queries and handlers with injected fresh UoWs.
5. Register handlers only at the event-bus composition root.
6. Return route templates, not resolved IDs/URLs. Add private cache headers.
7. With two process-like caches, toggle one action off and observe admission
   disabled within 30 seconds while lookup of an existing operation still works.

## Compatibility Matrix

| Client / backend | Behavior |
|---|---|
| Old client / new backend | Ignores new GET routes; legacy writes unchanged |
| New client / old backend | Manifest 404/invalid => `neverAutoRetry` |
| New/new, flag off | One-attempt legacy flow; no operation fields; lookup still available |
| New/new, flag on | Header+body contract; lookup before resend |
| Cached manifest expired | Disabled until fresh manifest succeeds |

## Verification Commands

```bash
uv run pytest tests/unit/app/handlers/query_handlers/reliable_write tests/unit/api/test_reliable_write_routes.py
uv run ruff check src/app/services/reliable_write src/app/queries/reliable_write src/app/handlers/query_handlers/reliable_write src/api/routes/v1/reliable_writes.py
```

## Success Criteria

- [ ] Manifest is authenticated, versioned, allowlisted, TTL-bound, and private.
- [ ] Missing capability, DB error, stale manifest, and unknown version fail closed.
- [ ] Lookup cannot enumerate another user's operations.
- [ ] Suggestion exists in registry, migration, manifest, lookup, route, tests,
  and rollout with its own false capability.
- [ ] Every status schema has a backward-compatible JSON fixture.

## Risks and Security

The generic `/v1/feature-flags/` endpoint is not the mobile contract. Never
include admin metadata, user identifiers, cross-owner operation existence, or
raw terminal error details.

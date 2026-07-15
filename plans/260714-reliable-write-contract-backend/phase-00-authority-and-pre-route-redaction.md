---
phase: 0
title: "Authority and Pre-route Redaction"
status: in-progress
priority: P1
dependencies: []
effort: "2-3 engineering days"
---

# Phase 0: Authority and Pre-route Redaction

## Overview

Correct repository authority and remove sensitive data before any reliable-write
migration, lookup route, or capability API can deploy. This is a hard prerequisite
for Phase 1, not rollout work.

## Review Status — 2026-07-15

Authority, strict PostgreSQL marker registration, and the provider redaction
foundation are implemented and focused tests pass. This phase remains incomplete:
generic string `path` telemetry is still accepted, and the planned exception,
provider-neutral observability, and real-PostgreSQL SQL sentinel suites do not
yet exist. Phase 1 and Phase 2 remain blocked.

## Requirements

- `AGENTS.md` names PostgreSQL/Neon and permits typed command results while
  retaining side-effect-only asynchronous events and the fiber-aware calorie rule.
- `docs/cqrs-guide.md` defines the typed command-result/UoW boundary: no
  handler-to-handler dispatch and no route-owned commit.
- Pre-routing/completion logs use only method/request class and FastAPI route
  template (or fixed `unmatched`), never a resolved URL/path, query, identity,
  body, or exception/database text.
- Sentry/metrics/event-bus/SQL observability are allowlist boundaries; SQL spans
  retain only fixed operation/table metadata or are dropped.
- Generic path telemetry is removed. A path-like value is accepted only when it
  originates from a trusted FastAPI route-template resolver; otherwise omit it
  or emit fixed `unmatched`. Resolved Firebase UIDs and other non-UUID dynamic
  segments must fail the same sentinels as UUIDs.

## Related Code Files

- Modify: `AGENTS.md`, `docs/cqrs-guide.md`.
- Modify: `src/api/middleware/request_logger.py`, `src/api/exception_handlers.py`,
  `src/infra/event_bus/pymediator_event_bus.py`, `src/observability.py`,
  `src/infra/monitoring/sentry.py`.
- Create: `tests/unit/api/middleware/test_reliable_write_request_redaction.py`,
  `tests/unit/api/test_reliable_write_exception_redaction.py`,
  `tests/unit/infra/monitoring/test_reliable_write_observability.py`,
  `tests/unit/infra/monitoring/test_reliable_write_sentry_redaction.py`, and
  `tests/integration/infra/test_reliable_write_sql_redaction.py`.

## Implementation Steps

1. Add sentinel tests first for UID, operation/entity IDs, resolved lookup path,
   fingerprint, URL/code/weight, SQL bind value, and exception text.
2. Replace resolved route data with a shared trusted route-template helper;
   apply it in request middleware and exception handling with an `unmatched`
   fallback. Remove the generic string `path` allowlist from provider-neutral
   observability and Sentry connectors.
3. Restrict event-bus and provider payloads to class/stage/outcome/version,
   bounded count, and duration. Remove user context, breadcrumbs/body/header/query
   capture, exception values, and SQL values.
4. Add the missing exception-handler, provider-observability, and SQL redaction
   suites listed above, then run unit and real-PostgreSQL sentinel tests. A
   sentinel occurrence in a log,
   metric, Sentry event/transaction/span, or SQL payload blocks Phase 1.

## Success Criteria

- [x] Authority documents match the current PostgreSQL and typed-command runtime.
- [ ] All sentinel redaction tests pass, including SQL and event-bus paths.
- [ ] Generic path telemetry is absent or validated as a trusted FastAPI route
  template; dynamic non-UUID path segments cannot reach any connector.
- [ ] No reliable-write migration, lookup, or API route is deployed before this
  phase completes.

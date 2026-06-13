---
title: "Sentry Observability Connector"
description: "Abstract existing Sentry monitoring behind a provider-neutral observability connector, migrate direct SDK call sites, and document operational setup."
status: completed
priority: P2
effort: "2-3 days"
branch: "delivery"
tags: [backend, infra, observability, refactor]
blockedBy: []
blocks: []
created: "2026-06-13T05:40:10.189Z"
createdBy: "ck:plan"
source: skill
mode: tdd
brainstorm: "../reports/260613-1236-sentry-observability-connector-brainstorm.md"
---

# Sentry Observability Connector

## Overview

Implement the approved Sentry observability connector design. The backend already has Sentry installed and initialized, but cron and infra services still import `sentry_sdk` directly. This plan keeps Sentry as an infrastructure-only connector behind a small app-owned facade.

Expected output: code, tests, and docs that preserve current Sentry behavior while making API, cron, and infra call sites provider-neutral.

Acceptance criteria:
- `rg "import sentry_sdk|sentry_sdk\\." src` only matches the Sentry connector.
- App startup initializes observability before `FastAPI(...)`.
- App imports and runs with `SENTRY_DSN` unset.
- Sentry event contract is implemented: unexpected failures and operational alerts are sent; expected 4xx/business errors and sensitive payloads are not sent.
- Request context includes request ID, method, route/path, environment, release, and safe user ID when available.
- Cron jobs capture/flush through the facade.
- Affiliate permanent failures alert through the facade.
- No request bodies, auth headers, Firebase tokens, email, food payloads, raw image URLs, or secrets are attached to events.
- Focused tests pass before broader lint/type/test gates.

## Scope Challenge

- Existing code: `src/infra/monitoring/sentry.py`, Sentry settings, request ID middleware, cron tests, and affiliate outbox tests already solve part of the problem.
- Minimum changes: add facade/no-op/Sentry connector, wire startup/request context, migrate four direct SDK call sites, update tests/docs.
- Complexity: touches more than 8 files but only one concern. Four TDD phases are warranted. No OpenTelemetry rewrite, no new observability platform.
- Selected mode: HOLD SCOPE with `--tdd`. User approved full coverage of errors, traces/profiles, cron, docs, and alert/dashboard setup guidance.

## Architecture Direction

```text
API startup / middleware / cron / infra service
        |
        v
src.infra.monitoring.observability facade
        |
        +-- NoopObservabilityConnector when disabled
        |
        +-- SentryObservabilityConnector
                |
                v
            sentry_sdk
```

Rules:
- Domain layer imports no monitoring code.
- Application layer avoids explicit monitoring unless a caught exception would otherwise be invisible.
- `sentry_sdk` imports stay inside `src/infra/monitoring/sentry.py`.
- Explicit captures are for caught failures and permanent operational alerts only; logging integration handles uncaught `ERROR` logs.
- Context is allowlisted, never copied wholesale from requests or exception details.

## Sentry Event Contract

Send:
- Unhandled API exceptions and unexpected 500-class failures.
- `ERROR` logs with exception info through Sentry logging integration.
- Caught-and-swallowed cron failures.
- Affiliate outbox permanent failures.
- Sampled FastAPI/Starlette request transactions.
- Sampled SQLAlchemy spans.
- Coarse cron phase and affiliate batch spans.
- Sampled profiles.

Do not send:
- 4xx validation/auth/not-found errors as issues.
- Expected business exceptions.
- Product analytics or audit logs.
- Request/response bodies, auth headers, Firebase tokens/claims, emails, food payloads, raw image URLs, raw provider payloads, or secrets.
- Debug/info logs as events.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Connector Contract and Regression Tests](./phase-01-connector-contract-and-regression-tests.md) | Completed |
| 2 | [Sentry Connector and API Context Wiring](./phase-02-sentry-connector-and-api-context-wiring.md) | Completed |
| 3 | [Cron and Infra Call Site Migration](./phase-03-cron-and-infra-call-site-migration.md) | Completed |
| 4 | [Documentation and Release Verification](./phase-04-documentation-and-release-verification.md) | Completed |

## Dependencies

- Brainstorm report: `plans/reports/260613-1236-sentry-observability-connector-brainstorm.md`
- Relevant docs: `docs/external-services.md`, `docs/system-architecture.md`, `docs/project-roadmap.md`
- Active pending plan note: `plans/260612-1046-service-initiated-bandwidth-reduction/` may also touch docs, but code file overlap is not expected.
- Runtime dependency already present: `sentry-sdk[fastapi]>=2.18.0`

## Validation

Focused gates:
- `pytest tests/unit/infra/monitoring tests/unit/api/middleware/test_request_logger.py tests/unit/cron/test_email_cron.py tests/unit/cron/test_push_cron.py tests/unit/infra/services/test_affiliate_outbox_dispatch_service.py -q`
- `pytest tests/unit/api/test_api_main_firebase_and_lifespan.py tests/unit/api/test_exceptions_unexpected.py -q`
- `rg "import sentry_sdk|sentry_sdk\\." src`

Release gates:
- `ruff check src tests`
- `mypy src`
- `pytest`

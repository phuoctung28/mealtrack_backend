---
title: "Sentry Logs Metrics Profiles"
description: "Extend the observability connector with Sentry Logs, provider-neutral metrics, and explicit profiling settings while keeping Sentry SDK isolated."
status: completed
priority: P2
effort: "1 day"
branch: "delivery"
tags: [backend, infra, observability, sentry]
blockedBy: []
blocks: []
created: "2026-06-13T06:09:18.793Z"
createdBy: "ck:plan"
source: skill
mode: tdd
brainstorm: "../reports/260613-1308-sentry-logs-metrics-profiles-brainstorm.md"
---

# Sentry Logs Metrics Profiles

## Overview

Extend the existing provider-neutral observability facade so MealTrack can use Sentry Logs, Sentry application metrics, and explicit profiling controls without leaking `sentry_sdk` into API, cron, app, or domain code.

This is an extension of completed plan `plans/260613-1239-sentry-observability-connector/plan.md`.

Acceptance criteria:

- `rg "import sentry_sdk|sentry_sdk\\." src` only matches `src/infra/monitoring/sentry.py`.
- Sentry init can pass `enable_logs`, `enable_metrics`, `profile_session_sample_rate`, and `profile_lifecycle` from settings.
- Facade exposes provider-neutral log and metric calls.
- No-op connector accepts log/metric calls without raising.
- Sentry connector maps facade calls to `sentry_sdk.logger` and `sentry_sdk.metrics`.
- Log and metric attributes are allowlisted scalar values only.
- Existing error-event behavior remains: debug/info logs do not become Sentry issues.
- Docs explain Logs vs Python logging integration, metrics, profiles, privacy, and sampling.

## Architecture Direction

```text
API / cron / infra services
        |
        v
src.infra.monitoring facade
        |
        +-- NoopObservabilityConnector
        |
        +-- SentryObservabilityConnector
                |
                +-- sentry_sdk.init(enable_logs, enable_metrics, profiling)
                +-- sentry_sdk.logger.*
                +-- sentry_sdk.metrics.*
```

Rules:

- Domain layer imports no monitoring code.
- App layer avoids observability unless a caught exception/log/metric would otherwise be invisible.
- Sentry SDK imports stay inside `src/infra/monitoring/sentry.py`.
- Metrics are operational only, not product analytics.
- Context, log attributes, and metric attributes use the same safe allowlist.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Sentry Init Settings and Regression Tests](./phase-01-sentry-init-settings-and-regression-tests.md) | Completed |
| 2 | [Facade Logs and Metrics API](./phase-02-facade-logs-and-metrics-api.md) | Completed |
| 3 | [Sentry Connector Routing and Privacy Filters](./phase-03-sentry-connector-routing-and-privacy-filters.md) | Completed |
| 4 | [Documentation and Verification](./phase-04-documentation-and-verification.md) | Completed |

## Dependencies

- Brainstorm report: `plans/reports/260613-1308-sentry-logs-metrics-profiles-brainstorm.md`
- Previous connector plan: `plans/260613-1239-sentry-observability-connector/plan.md`
- Current source:
  - `src/infra/config/settings.py`
  - `src/infra/monitoring/connectors.py`
  - `src/infra/monitoring/observability.py`
  - `src/infra/monitoring/sentry.py`
  - `src/infra/monitoring/__init__.py`
- Current tests:
  - `tests/unit/infra/monitoring/test_observability_facade.py`
  - `tests/unit/infra/monitoring/test_sentry_connector.py`
- Docs:
  - `docs/external-services.md`
  - `docs/system-architecture.md`
  - `docs/troubleshooting.md`

## Validation

Focused gates:

- `pytest tests/unit/infra/monitoring -q`
- `pytest tests/unit/api/middleware/test_request_logger.py tests/unit/cron/test_email_cron.py tests/unit/cron/test_push_cron.py tests/unit/infra/services/test_affiliate_outbox_dispatch_service.py -q`
- `rg "import sentry_sdk|sentry_sdk\\." src`
- `mypy src/infra/monitoring src/infra/services/affiliate_outbox_dispatch_service.py`
- `ruff check src/infra/monitoring src/infra/config/settings.py tests/unit/infra/monitoring`

Release gates:

- `pytest`
- `ruff check src tests` may still expose unrelated existing repo-wide lint debt; do not mass-fix unrelated files.
- `mypy src` may still expose unrelated existing repo-wide type debt; do not mass-fix unrelated files.

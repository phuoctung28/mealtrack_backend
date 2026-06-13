---
phase: 1
title: "Connector Contract and Regression Tests"
status: completed
priority: P1
effort: "4-6h"
dependencies: []
---

# Phase 1: Connector Contract and Regression Tests

## Context Links

- Plan: `plans/260613-1239-sentry-observability-connector/plan.md`
- Brainstorm: `plans/reports/260613-1236-sentry-observability-connector-brainstorm.md`
- Current Sentry module: `src/infra/monitoring/sentry.py`
- Current request middleware: `src/api/middleware/request_logger.py`
- Current API startup: `src/api/main.py`

## Overview

Define the small provider-neutral observability contract and lock current behavior with tests before moving SDK calls. This phase should create the seam while keeping current Sentry startup behavior intact.

## Key Insights

- Sentry is already optional: no DSN means disabled.
- Startup ordering matters: Sentry/FastAPI instrumentation must initialize before `FastAPI(...)`.
- Tests should target app-owned behavior, not Sentry internals.
- Global connector state needs a test reset path to prevent order-dependent failures.

## Requirements

Functional:
- Add an observability facade and no-op connector.
- Keep existing `initialize_sentry()` compatibility only if needed during migration.
- Provide safe context filtering helpers.
- Encode the event context allowlist and unsafe-key rejection in tests.
- Add tests for no-op behavior and context allowlist behavior.

Non-functional:
- No domain imports of monitoring.
- No network calls in tests.
- Connector functions never raise when monitoring is disabled.
- Files should stay under code-size targets; split protocol/no-op/facade if needed.

## Architecture

Create a facade that owns global connector state:

```text
observability.py
  initialize_observability()
  capture_exception()
  capture_message()
  set_request_context()
  start_span()
  flush()
  set_observability_connector_for_test()
  reset_observability_connector_for_test()

connectors.py
  ObservabilityConnector Protocol
  NoopObservabilityConnector
  ObservabilitySpan / noop context manager
```

## Related Code Files

- Create: `src/infra/monitoring/connectors.py`
- Create: `src/infra/monitoring/observability.py`
- Modify: `src/infra/monitoring/__init__.py`
- Create: `tests/unit/infra/monitoring/test_observability_facade.py`
- Create: `tests/unit/infra/monitoring/test_observability_context.py`

## Implementation Steps

### Tests Before

1. Add tests proving no-op facade calls never raise.
2. Add tests proving unsafe context keys are dropped.
3. Add tests proving test connector override/reset isolates global state.
4. Add tests proving `start_span()` can be used as a context manager when disabled.
5. Add tests proving event context keeps only approved keys: `request_id`, `method`, `path`, `status_code`, `elapsed_ms`, `environment`, `release`, `user_id`, `component`, `operation`, `error_type`, `row_id`, `event_id`, `event_type`, `attempt_count`.

### Refactor

1. Define `ObservabilityConnector` protocol with:
   - `initialize() -> None`
   - `capture_exception(exc, context=None, tags=None) -> None`
   - `capture_message(message, level="error", context=None, tags=None) -> None`
   - `set_request_context(request_id, method, path, user_id=None) -> None`
   - `start_span(op, description=None, data=None)`
   - `flush(timeout=5.0) -> None`
2. Implement `NoopObservabilityConnector`.
3. Implement facade functions that delegate to current connector.
4. Add context/tag allowlist helper. Use explicit keys only.
5. Export facade functions from monitoring package.

### Tests After

1. Add coverage for unknown context keys and unsafe obvious names (`authorization`, `token`, `email`, `body`, `image_url`).
2. Add coverage for `None` context/tags.

### Regression Gate

Run:

```bash
pytest tests/unit/infra/monitoring -q
```

## Success Criteria

- [ ] Observability facade exists and is provider-neutral.
- [ ] No-op connector is default-safe.
- [ ] Context filter allowlists only safe keys.
- [ ] Tests prove disabled monitoring never raises.
- [ ] Domain layer remains untouched.

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Facade hides errors that should fail fast | Silent monitoring bugs | Log connector initialization failures locally |
| Global state leaks across tests | Flaky tests | Provide explicit test reset helper |
| Overbroad context filtering | PII leak | Allowlist, not denylist |

## Security Considerations

- No request bodies or headers in context.
- No raw exception details copied into context by default.
- User identifier must be internal UUID only, not email.

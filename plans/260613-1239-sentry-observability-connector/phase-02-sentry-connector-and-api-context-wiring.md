---
phase: 2
title: "Sentry Connector and API Context Wiring"
status: completed
priority: P1
effort: "5-7h"
dependencies: [1]
---

# Phase 2: Sentry Connector and API Context Wiring

## Context Links

- Plan: `plans/260613-1239-sentry-observability-connector/plan.md`
- Phase 1: `phase-01-connector-contract-and-regression-tests.md`
- API startup: `src/api/main.py`
- Request middleware: `src/api/middleware/request_logger.py`
- Exception mapping: `src/api/exceptions.py`

## Overview

Move Sentry SDK ownership into `SentryObservabilityConnector`, preserve startup timing, and attach safe request context from middleware.

## Key Insights

- `initialize_observability()` must run before `FastAPI(...)`.
- Sentry FastAPI/Starlette/SQLAlchemy/logging integrations should remain.
- Request context belongs in middleware because it already owns `request_id` and timing.
- Explicit `capture_exception()` in generic exception handling is optional; logging integration already captures `ERROR`, but adding explicit capture gives deterministic context if deduped carefully.

## Requirements

Functional:
- Convert current `initialize_sentry()` module behavior into `SentryObservabilityConnector`.
- Wire `src/api/main.py` to `initialize_observability()`.
- Attach request context in `RequestLoggerMiddleware`.
- Capture only unexpected API failures explicitly; expected 4xx/business errors stay out of Sentry issue creation.
- Keep existing `SENTRY_DSN`, trace/profile rates, and PII toggle behavior.
- Add `SENTRY_RELEASE` and optional `SENTRY_ENABLE_LOGS` config if implementation confirms SDK support.

Non-functional:
- Sentry import isolated to `src/infra/monitoring/sentry.py`.
- Startup import with missing DSN still succeeds.
- Request context must not read body or sensitive headers.

## Architecture

```text
src/api/main.py
  initialize_observability()
  app = FastAPI(...)

RequestLoggerMiddleware
  generate request_id
  set request.state.request_id
  set_request_context(...)
```

`SentryObservabilityConnector` maps facade calls to SDK calls. Use the current Sentry SDK v2 preferred APIs where practical, but keep behavior stable if top-level aliases are unavoidable in this version.

## Related Code Files

- Modify: `src/infra/monitoring/sentry.py`
- Modify: `src/infra/config/settings.py`
- Modify: `src/api/main.py`
- Modify: `src/api/middleware/request_logger.py`
- Modify if needed: `src/api/exceptions.py`
- Create: `tests/unit/infra/monitoring/test_sentry_connector.py`
- Modify: `tests/unit/api/test_api_main_firebase_and_lifespan.py`
- Modify: `tests/unit/api/middleware/test_request_logger.py`

## Implementation Steps

### Tests Before

1. Add tests that import `src.api.main` with `SENTRY_DSN` unset and assert no crash.
2. Add tests that patch the connector and assert `initialize_observability()` is called before app creation path remains import-safe.
3. Add middleware test asserting `set_request_context()` receives `request_id`, method, and path.
4. Add Sentry connector test that patches SDK module and asserts init options include integrations and sample rates.

### Refactor

1. Move initialization logic into `SentryObservabilityConnector.initialize()`.
2. Make `initialize_observability()` choose no-op when Sentry is unavailable or disabled.
3. Update `src/api/main.py` import and module-level initialization.
4. Update middleware to call facade context setter after request ID generation.
5. Add safe release config pass-through.
6. Decide explicit unexpected exception capture in `handle_exception()`:
   - If used, capture only unexpected exceptions.
   - Do not explicitly capture expected `MealTrackException`, `HTTPException`, or `AIUnavailableError`.
   - Never attach request/response body, auth headers, full Firebase claims, email, food payload, raw image URL, or raw provider payload.

### Tests After

1. Verify existing request logger tests still pass.
2. Verify generic exception response still redacts internal exception text.
3. Verify disabled Sentry path logs locally and does not fail startup.

### Regression Gate

Run:

```bash
pytest tests/unit/infra/monitoring tests/unit/api/middleware/test_request_logger.py tests/unit/api/test_api_main_firebase_and_lifespan.py tests/unit/api/test_exceptions_unexpected.py -q
```

## Success Criteria

- [ ] Sentry connector owns all SDK init behavior.
- [ ] API startup uses provider-neutral initialization.
- [ ] Request context is attached through facade.
- [ ] Expected API exceptions are not explicitly captured as Sentry errors.
- [ ] Tests pass with DSN absent.

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Init after app creation breaks FastAPI instrumentation | Missing traces/errors | Keep module-level init before `FastAPI(...)` |
| Explicit capture duplicates logging integration events | Sentry noise | Capture only caught unexpected exceptions if needed |
| Request context includes unsafe user data | Privacy issue | Use allowlist and internal UUID only |

## Security Considerations

- Keep `SENTRY_SEND_PII=false` default.
- No request body or raw URL query parameters in custom context.
- Do not pass Firebase claims wholesale.

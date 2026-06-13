---
type: brainstorm
date: 2026-06-13
topic: sentry observability connector abstraction
status: approved-design
approved_approach: connector facade with sentry as infrastructure adapter
---

# Brainstorm: Sentry Observability Connector

## Summary

MealTrack already has Sentry installed and partially wired. The approved direction is not a first-time integration; it is a cleanup and abstraction pass.

Sentry should become one infrastructure connector behind a small provider-neutral observability facade. API startup, request middleware, cron entry points, and infra services should call the facade. Only the Sentry connector should import `sentry_sdk`.

## Codebase Findings

- `pyproject.toml` and `requirements.txt` already include `sentry-sdk[fastapi]>=2.18.0`.
- `src/infra/config/settings.py` already defines `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE`, `SENTRY_PROFILES_SAMPLE_RATE`, and `SENTRY_SEND_PII`.
- `src/infra/monitoring/sentry.py` already initializes Sentry with FastAPI, Starlette, SQLAlchemy, and logging integrations.
- `src/api/main.py` initializes Sentry before `FastAPI(...)`, which is the correct timing for framework instrumentation.
- Direct SDK coupling still exists in cron and infra paths:
  - `src/cron/email.py`
  - `src/cron/push.py`
  - `src/cron/affiliate_outbox.py`
  - `src/infra/services/affiliate_outbox_dispatch_service.py`
- `src/api/middleware/request_logger.py` already owns request IDs and safe request timing logs.
- `docs/external-services.md` already treats Sentry as a graceful-degradation external service.

## Requirements

### Expected Output

- Implementation plan for a provider-neutral observability connector.
- Sentry remains the only concrete connector for now.
- API, cron, and infra services no longer depend directly on `sentry_sdk`.
- Docs include Sentry runtime config, privacy rules, and operations checklist.

### Acceptance Criteria

- `rg "import sentry_sdk|sentry_sdk\\." src` only matches Sentry connector code.
- App startup still initializes monitoring before `FastAPI(...)`.
- App works when `SENTRY_DSN` is unset.
- Unexpected API errors are captured with request context.
- Cron failures and permanent affiliate outbox failures are captured through the abstraction.
- Flush behavior at cron shutdown is preserved through the abstraction.
- Sentry events do not include request bodies, auth headers, Firebase tokens, email addresses, food payloads, or raw image URLs.
- Tests cover no-op behavior, Sentry-enabled behavior, request context, cron wiring, and permanent failure alert wiring.

### Scope Boundary

Included:

- Error capture.
- Message capture.
- Sentry FastAPI, Starlette, SQLAlchemy, logging, tracing, and profiling setup.
- Request context: request ID, method, route/path, environment, release, safe user identifier.
- Cron capture and flush.
- Affiliate outbox permanent-failure alert capture.
- Basic docs for Sentry config, privacy policy, alert checklist, dashboard checklist, and release tagging.

Out of scope unless explicitly approved later:

- Sentry project creation.
- Sentry alert/dashboard automation through Sentry API.
- New business monitoring requirements beyond errors, traces, profiles, and operational messages.
- Replacing PostHog LLM analytics.
- Replacing request logging.

## Approaches Evaluated

### Approach A - Minimal Wrapper Around Current Sentry Module

Keep `src/infra/monitoring/sentry.py`, add helper functions, and update direct SDK users to call those helpers.

Pros:

- Fastest.
- Smallest file change.
- Good enough for current direct `flush()` and `capture_message()` calls.

Cons:

- Weak abstraction.
- Harder to test no-op vs Sentry behavior cleanly.
- Name still makes Sentry feel like the application contract.
- Future provider changes would touch more call sites.

Decision: rejected.

### Approach B - Connector Facade With No-Op and Sentry Connector

Create a small observability facade in `src/infra/monitoring`. The facade exposes provider-neutral operations and delegates to either `NoopObservabilityConnector` or `SentryObservabilityConnector`.

Pros:

- Best balance of clean architecture and low complexity.
- Keeps SDK calls in one file.
- Lets cron/API/infra code depend on app-owned vocabulary.
- Easy tests with fake/no-op connector.
- Keeps Sentry optional and graceful.

Cons:

- Adds a small abstraction layer.
- Needs careful naming so it does not become a broad metrics platform.

Decision: approved.

### Approach C - Full OpenTelemetry / Vendor-Neutral Observability Layer

Use OpenTelemetry as the main abstraction for errors, traces, metrics, and logs.

Pros:

- Strong vendor neutrality.
- Better if multiple telemetry backends are required.

Cons:

- Overkill now.
- More operational complexity.
- Duplicates existing PostHog OpenTelemetry setup concerns.
- Error capture ergonomics are worse than direct Sentry SDK features.

Decision: rejected.

## Final Recommended Solution

Use Approach B.

Target shape:

```text
src/infra/monitoring/
├── __init__.py
├── observability.py          # facade + get/set connector helpers
├── connectors.py             # Protocol/base types + no-op connector
└── sentry.py                 # Sentry-only implementation and SDK imports
```

Core facade operations:

- `initialize_observability()`
- `capture_exception(exc, context=None, tags=None)`
- `capture_message(message, level="error", context=None, tags=None)`
- `set_request_context(request_id, method, path, user_id=None)`
- `start_span(op, description=None, data=None)`
- `flush(timeout=5.0)`

Usage rules:

- API startup calls `initialize_observability()` before `FastAPI(...)`.
- Request middleware sets request context after generating `request_id`.
- Cron entry points call `initialize_observability()` and `flush()`.
- Infra services call `capture_message()` or `capture_exception()` only through the facade.
- Domain layer does not import monitoring.
- Application layer avoids explicit monitoring unless a use case has a product-critical failure that framework logging cannot capture.

## Request Context Policy

Allowed:

- `request_id`
- HTTP method
- route/path
- status code
- elapsed milliseconds
- environment
- release
- internal user UUID when available

Not allowed:

- request/response body
- Authorization header
- Firebase token
- service account JSON
- emails
- food descriptions
- raw OCR/AI payloads
- raw image URLs
- payment/referral secrets

## Sentry Event Contract

Send these:

- Unhandled API exceptions and unexpected 500-class failures.
- `ERROR` logs with exception info through Sentry logging integration.
- Cron failures that are caught and swallowed, especially database warm-up failure and top-level cron failure.
- Affiliate outbox permanent failures as explicit `capture_message`.
- FastAPI/Starlette request transactions through sampling.
- SQLAlchemy spans through sampling.
- Coarse custom spans for cron phases and affiliate batch dispatch.
- Profiles through conservative sample rate.

Do not send these:

- 4xx validation, auth, not-found, or expected business errors as Sentry issues.
- Normal product analytics or audit events.
- Per-row affiliate dispatch spans.
- Request/response bodies.
- Authorization headers.
- Firebase tokens or full claims.
- Emails.
- Food descriptions, meal text, OCR, AI raw provider payloads, or image bytes.
- Raw image URLs.
- RevenueCat raw webhook payloads.
- Database URLs, API keys, HMAC secrets, or service credentials.
- Debug/info logs as Sentry events.

Allowed event context:

- `request_id`
- `method`
- normalized `path` or route
- `status_code`
- `elapsed_ms`
- `environment`
- `release`
- internal `user_id` when available
- `component`: `api`, `cron`, `affiliate_outbox`
- `operation`: e.g. `email_cron`, `push_cron`, `affiliate_dispatch`
- `error_type`

Affiliate permanent-failure context:

- `row_id`
- `event_id`
- `event_type`
- `attempt_count` if available

## Sentry Configuration Policy

Existing config stays:

- `SENTRY_DSN`
- `SENTRY_TRACES_SAMPLE_RATE`
- `SENTRY_PROFILES_SAMPLE_RATE`
- `SENTRY_SEND_PII`

Recommended additions:

- `SENTRY_ENABLED` default derived from DSN presence.
- `SENTRY_RELEASE` pass-through to Sentry SDK.
- `SENTRY_ENABLE_LOGS` optional, default false until log volume is understood.

Sampling:

- Production traces default `0.1`.
- Profiles default `0.05` or lower.
- Dev/test should default disabled unless explicitly configured.

## Operations Checklist

Docs should include a checklist for manual Sentry setup:

- Create project and set `SENTRY_DSN`.
- Set environment-specific DSNs or environment tags.
- Set `SENTRY_RELEASE` in deploy environment.
- Alert on new high-severity errors.
- Alert on repeated cron failures.
- Alert on affiliate outbox permanent failures.
- Dashboard cards:
  - 5xx rate by route
  - slowest API transactions
  - cron failure count
  - top exception classes
  - external provider error rate

Automation through Sentry API is optional later. It needs a Sentry auth token and is not necessary for the backend connector abstraction.

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Abstraction becomes too broad | Extra complexity | Keep only error/message/context/span/flush for now |
| Duplicate error capture from logging integration and explicit calls | Noisy Sentry issues | Explicit capture only for caught exceptions and permanent operational failures |
| PII leaks through context | Security/privacy issue | Allowlist context keys; no body/header capture |
| Sentry SDK API changes | Future breakage | SDK calls stay in `SentryObservabilityConnector` only |
| High trace/profile volume | Cost/noise | Conservative sample rates and env-driven tuning |
| Test flakiness from global connector state | Unstable tests | Provide reset/set helper for tests |

## Validation Criteria

- Unit: no-op connector never raises.
- Unit: Sentry connector calls SDK init with configured integrations and sample rates.
- Unit: context allowlist excludes unsafe keys.
- Unit: request middleware sets request context with request ID.
- Unit: cron jobs call facade `flush()` on exit and warm-up failure.
- Unit: affiliate outbox permanent failure calls facade `capture_message()`.
- Search: no direct SDK imports outside Sentry connector.
- Smoke: import `src.api.main` with `SENTRY_DSN` unset does not crash.

## Next Steps

1. Create an implementation plan from this report.
2. Implement the connector facade and no-op/Sentry connectors.
3. Migrate direct SDK call sites.
4. Add tests around connector behavior and migrated call sites.
5. Update `docs/external-services.md`, `docs/project-roadmap.md`, and possibly `docs/system-architecture.md`.

## Unresolved Questions

- Should Sentry dashboard/alert creation stay as a manual docs checklist, or should a future phase automate it with the Sentry API?

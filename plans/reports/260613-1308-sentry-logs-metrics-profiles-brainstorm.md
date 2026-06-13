---
type: brainstorm
date: 2026-06-13
topic: sentry logs metrics profiles connector extension
status: approved-design
approved_approach: extend observability facade with sentry logs metrics and profiling config
sources:
  - https://docs.sentry.io/platforms/python/logs/
  - https://docs.sentry.io/platforms/python/metrics/
  - https://docs.sentry.io/platforms/python/profiling/
---

# Brainstorm: Sentry Logs Metrics Profiles

## Summary

MealTrack now has a provider-neutral observability facade with Sentry isolated as the infrastructure connector. The missing piece is Sentry Logs and first-class metrics facade support.

Approved direction: extend the existing facade. Do not let application code import `sentry_sdk.logger` or `sentry_sdk.metrics` directly.

## Codebase Findings

- Project is FastAPI + Python 3.11+ with SQLAlchemy async runtime.
- `src/infra/monitoring/sentry.py` is the only source file that imports or calls `sentry_sdk`.
- Current Sentry init passes DSN, environment, release, trace sample rate, profile sample rate, PII setting, and FastAPI/Starlette/SQLAlchemy/logging integrations.
- Current logging integration sends Python `ERROR` logs as Sentry events and `INFO+` logs as breadcrumbs, but Sentry Logs are not enabled because `enable_logs=True` is absent.
- Installed SDK default options include `enable_logs=False`, `enable_metrics=True`, `before_send_log`, `before_send_metric`, `profile_session_sample_rate`, and `profile_lifecycle`.
- `sentry_sdk.metrics` is available locally with `count`, `gauge`, and `distribution`.
- Existing docs already describe Sentry as a connector-backed observability provider.
- Related completed plan: `plans/260613-1239-sentry-observability-connector/plan.md`.

## Requirements

### Expected Output

- A TDD implementation plan to enable Sentry Logs, expose metrics through the observability facade, and tighten profiling config.
- No implementation in brainstorm phase.

### Acceptance Criteria

- `sentry_sdk` imports and calls still only appear in `src/infra/monitoring/sentry.py`.
- `enable_logs=True` can be configured through settings.
- Logs can be emitted through the facade and routed to Sentry Logs when enabled.
- Metrics can be emitted through facade methods and routed to Sentry metrics when enabled.
- Profile config supports current transaction profiling and optional session profiling settings.
- Log and metric attributes are allowlisted scalar values only.
- Existing error event contract remains unchanged: debug/info logs do not become Sentry issues.
- Tests cover disabled/no-op behavior, enabled Sentry init args, log routing, metric routing, and sensitive attribute filtering.

### Scope Boundary

Included:

- Sentry Logs SDK option.
- Provider-neutral log facade method.
- Provider-neutral metric facade methods for counter, gauge, and distribution.
- Config toggles for logs, metrics, and optional profile session settings.
- Sentry connector implementation and tests.
- Docs update for logs, metrics, profiles, privacy, and sampling.

Out of scope:

- Direct application migration to emit large numbers of business logs.
- OpenTelemetry migration.
- Sentry project/API automation.
- Product analytics replacement.
- High-cardinality metric design beyond a small allowlist.
- Logging request bodies, auth data, Firebase claims, emails, food payloads, image URLs, provider payloads, or secrets.

## Approaches Evaluated

### Approach A - Only Pass `enable_logs=True`

Add `enable_logs=True` to `sentry_sdk.init`.

Pros:

- Fastest.
- Minimal code.

Cons:

- No env toggle.
- No explicit privacy filter for Sentry Logs.
- Does not solve metrics.
- Tempts future direct `sentry_sdk.logger` imports.

Verdict: too thin. Useful as part of final solution, not enough alone.

### Approach B - Extend Existing Observability Facade

Add log and metric operations to `src.infra.monitoring`, and keep Sentry SDK details in `src/infra/monitoring/sentry.py`.

Pros:

- Preserves abstraction.
- Testable.
- Keeps privacy filtering centralized.
- Covers logs, metrics, and profiles without new platform.
- Small, consistent with existing connector design.

Cons:

- Slightly larger API surface.
- Need careful naming so facade does not become a product analytics layer.

Verdict: recommended.

### Approach C - Introduce OpenTelemetry

Use OpenTelemetry for logs, metrics, traces, and export to Sentry.

Pros:

- Vendor-neutral long-term.
- Broad ecosystem.

Cons:

- Much larger change.
- Duplicates existing working Sentry connector.
- Unnecessary for current goal.

Verdict: over-engineered for this round.

## Final Recommended Design

Extend the existing observability connector.

Settings:

- `SENTRY_ENABLE_LOGS: bool = True`
- `SENTRY_ENABLE_METRICS: bool = True`
- `SENTRY_PROFILE_SESSION_SAMPLE_RATE: float | None = None`
- `SENTRY_PROFILE_LIFECYCLE: str | None = None`

Facade additions:

- `log_event(level, message, attributes=None)`
- `increment_metric(name, value=1.0, unit=None, attributes=None)`
- `gauge_metric(name, value, unit=None, attributes=None)`
- `distribution_metric(name, value, unit=None, attributes=None)`

Connector behavior:

- Sentry init passes `enable_logs=settings.SENTRY_ENABLE_LOGS`.
- Sentry init passes `enable_metrics=settings.SENTRY_ENABLE_METRICS`.
- If session profiling settings are configured, pass `profile_session_sample_rate` and `profile_lifecycle`.
- `log_event` maps to `sentry_sdk.logger.{level}`.
- Metric methods map to `sentry_sdk.metrics.count`, `gauge`, and `distribution`.
- All attributes flow through a safe scalar allowlist before provider calls.

## Privacy And Cardinality Rules

Allowed attributes:

- `request_id`
- `method`
- `route`
- `status_code`
- `environment`
- `release`
- `component`
- `operation`
- `error_type`
- `event_type`
- `row_id`
- `event_id`
- low-cardinality result/status labels

Blocked attributes:

- request/response bodies
- auth headers
- Firebase tokens or claims
- email addresses
- food payloads
- raw image URLs
- raw provider payloads
- secrets
- arbitrary user-generated text
- high-cardinality business identifiers unless explicitly allowlisted

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Log volume cost | Sentry cost/noise | Env toggle, conservative usage, no automatic debug/info issue creation |
| PII leakage | Security/privacy incident | Central allowlist + tests |
| Metric cardinality explosion | Expensive and hard to query | Restricted attributes only |
| Facade becomes analytics platform | Architecture drift | Keep API operational only, not product analytics |
| Profile overhead | Runtime overhead | Low/default sampling and env control |

## Success Metrics

- Source scan still isolates Sentry SDK to connector.
- Tests prove log and metric attributes are filtered.
- Sentry init test proves logs/metrics/profile settings are passed.
- Docs explain Logs vs logging integration vs error events.
- Production can search Sentry Logs and query operational metrics without direct SDK imports.

## Next Steps

- Create `/ck:plan --tdd` plan from this report.
- Implement tests first around init options, facade methods, connector routing, and filtering.
- Update docs after code.

## Unresolved Questions

- None. User approved enabling Sentry Logs, metrics, and profiles while preserving the connector abstraction.

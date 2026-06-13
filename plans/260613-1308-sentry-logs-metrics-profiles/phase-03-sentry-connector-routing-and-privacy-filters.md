---
phase: 3
title: "Sentry Connector Routing and Privacy Filters"
status: completed
effort: "medium"
---

# Phase 3: Sentry Connector Routing and Privacy Filters

## Context Links

- Plan: `plans/260613-1308-sentry-logs-metrics-profiles/plan.md`
- Sentry connector: `src/infra/monitoring/sentry.py`
- Context filters: `src/infra/monitoring/connectors.py`
- Tests: `tests/unit/infra/monitoring/test_sentry_connector.py`

## Overview

Priority: P2  
Status: Completed

Map facade log and metric methods to Sentry SDK calls while filtering attributes centrally.

## Requirements

- `log_event` maps to `sentry_sdk.logger.trace/debug/info/warning/error/fatal`.
- Unknown log levels normalize safely.
- Metric methods map to:
  - `sentry_sdk.metrics.count`
  - `sentry_sdk.metrics.gauge`
  - `sentry_sdk.metrics.distribution`
- Attributes are allowlisted scalar values only.
- Sensitive/high-cardinality values are dropped.
- `sentry_sdk` usage remains isolated to `src/infra/monitoring/sentry.py`.

## Architecture

Sentry connector owns SDK imports and provider-specific method mapping. Shared filter helpers remain provider-neutral.

## Related Code Files

Modify:

- `src/infra/monitoring/connectors.py`
- `src/infra/monitoring/sentry.py`
- `tests/unit/infra/monitoring/test_sentry_connector.py`

## Implementation Steps

1. Add failing tests for log routing:
   - enabled connector calls expected `sentry_sdk.logger` method.
   - disabled connector no-ops.
   - sensitive attributes dropped.
2. Add failing tests for metric routing:
   - count/gauge/distribution calls.
   - unit and attributes passed correctly.
   - sensitive/high-cardinality attributes dropped.
3. Add or reuse safe attribute filter.
4. Implement Sentry log routing.
5. Implement Sentry metric routing.
6. Run source scan and tests.

## Todo List

- [x] Add log routing tests.
- [x] Add metric routing tests.
- [x] Add/extend safe attribute filters.
- [x] Implement Sentry log routing.
- [x] Implement Sentry metric routing.
- [x] Run source scan.

## Success Criteria

- `pytest tests/unit/infra/monitoring/test_sentry_connector.py -q` passes.
- `rg "import sentry_sdk|sentry_sdk\\." src` only matches `src/infra/monitoring/sentry.py`.
- Tests prove raw payload-like attributes are dropped.

## Risk Assessment

- Metric cardinality can explode. Keep attribute allowlist small.
- Logs can duplicate existing Python logger events. Use facade intentionally for structured Sentry Logs, not blanket conversion of every app log.

## Security Considerations

Blocked attributes include:

- request/response bodies
- auth headers
- Firebase tokens/claims
- email addresses
- food payloads
- raw image URLs
- raw provider payloads
- secrets
- arbitrary user-generated text

## Next Steps

Proceed to docs and final verification.

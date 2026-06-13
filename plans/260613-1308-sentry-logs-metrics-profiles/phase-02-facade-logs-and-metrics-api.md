---
phase: 2
title: "Facade Logs and Metrics API"
status: completed
effort: "medium"
---

# Phase 2: Facade Logs and Metrics API

## Context Links

- Plan: `plans/260613-1308-sentry-logs-metrics-profiles/plan.md`
- Facade: `src/infra/monitoring/observability.py`
- Contract: `src/infra/monitoring/connectors.py`
- Exports: `src/infra/monitoring/__init__.py`
- Tests: `tests/unit/infra/monitoring/test_observability_facade.py`

## Overview

Priority: P2  
Status: Completed

Extend the provider-neutral observability facade with logs and metrics without exposing Sentry SDK types.

## Requirements

- Add connector protocol methods:
  - `log_event(level, message, attributes=None)`
  - `increment_metric(name, value=1.0, unit=None, attributes=None)`
  - `gauge_metric(name, value, unit=None, attributes=None)`
  - `distribution_metric(name, value, unit=None, attributes=None)`
- Add no-op implementations.
- Add facade functions and exports.
- Preserve current methods and tests.

## Architecture

API/cron/infra callers use facade functions only. Metrics/log attributes must use safe scalar attributes and must not become product analytics.

## Related Code Files

Modify:

- `src/infra/monitoring/connectors.py`
- `src/infra/monitoring/observability.py`
- `src/infra/monitoring/__init__.py`
- `tests/unit/infra/monitoring/test_observability_facade.py`

## Implementation Steps

1. Add failing facade delegation tests for log and metric calls.
2. Extend `ObservabilityConnector` protocol.
3. Extend `NoopObservabilityConnector`.
4. Add facade wrapper functions.
5. Export new functions from `src/infra/monitoring/__init__.py`.
6. Run focused tests.

## Todo List

- [x] Add facade delegation tests.
- [x] Extend connector protocol.
- [x] Extend no-op connector.
- [x] Add facade functions.
- [x] Export new functions.
- [x] Run focused tests.

## Success Criteria

- No-op connector accepts all log/metric calls without raising.
- Facade delegates exactly once with expected arguments.
- Existing facade tests still pass.

## Risk Assessment

- Too broad facade can turn into analytics layer. Keep names operational and documented.

## Security Considerations

- Do not add raw attribute passthrough in public API docs.
- Attribute filtering will be enforced in phase 3.

## Next Steps

Proceed to Sentry connector routing and privacy filters.

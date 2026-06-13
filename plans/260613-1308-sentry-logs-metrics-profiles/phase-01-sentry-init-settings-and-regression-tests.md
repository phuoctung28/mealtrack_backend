---
phase: 1
title: "Sentry Init Settings and Regression Tests"
status: completed
effort: "small"
---

# Phase 1: Sentry Init Settings and Regression Tests

## Context Links

- Plan: `plans/260613-1308-sentry-logs-metrics-profiles/plan.md`
- Brainstorm: `plans/reports/260613-1308-sentry-logs-metrics-profiles-brainstorm.md`
- Current connector: `src/infra/monitoring/sentry.py`
- Settings: `src/infra/config/settings.py`
- Tests: `tests/unit/infra/monitoring/test_sentry_connector.py`

## Overview

Priority: P2  
Status: Completed

Add config fields and tests for Sentry Logs, metrics, and explicit profile settings before changing connector behavior.

## Requirements

- Add settings:
  - `SENTRY_ENABLE_LOGS: bool`
  - `SENTRY_ENABLE_METRICS: bool`
  - `SENTRY_PROFILE_SESSION_SAMPLE_RATE: float | None`
  - `SENTRY_PROFILE_LIFECYCLE: str | None`
- Preserve existing settings:
  - `SENTRY_DSN`
  - `SENTRY_RELEASE`
  - `SENTRY_TRACES_SAMPLE_RATE`
  - `SENTRY_PROFILES_SAMPLE_RATE`
  - `SENTRY_SEND_PII`
- Tests must assert settings are passed to `sentry_sdk.init`.
- Tests must assert omitted optional profile settings are not forced if unset.

## Architecture

Settings remain infrastructure configuration. No API/domain/app layer setting reads.

## Related Code Files

Modify:

- `src/infra/config/settings.py`
- `src/infra/monitoring/sentry.py`
- `tests/unit/infra/monitoring/test_sentry_connector.py`
- `docs/external-services.md` later in phase 4

## Implementation Steps

1. Add failing tests in `tests/unit/infra/monitoring/test_sentry_connector.py` for init kwargs:
   - `enable_logs`
   - `enable_metrics`
   - `profile_session_sample_rate`
   - `profile_lifecycle`
2. Add settings defaults.
3. Update Sentry connector init kwargs.
4. Keep `SENTRY_DSN` unset path no-op.
5. Run focused tests.

## Todo List

- [x] Add init kwargs regression tests.
- [x] Add settings fields.
- [x] Pass new fields to Sentry init.
- [x] Run focused tests.

## Success Criteria

- `pytest tests/unit/infra/monitoring/test_sentry_connector.py -q` passes.
- Sentry init includes logs and metrics toggles.
- Existing no-DSN behavior unchanged.

## Risk Assessment

- `enable_logs=True` can increase volume. Mitigate with env toggle and docs.
- Session profiling can add overhead. Keep optional and explicitly configured.

## Security Considerations

- No new data capture should be added in this phase beyond SDK configuration.
- `SENTRY_SEND_PII=false` remains default.

## Next Steps

Proceed to facade API for logs and metrics.

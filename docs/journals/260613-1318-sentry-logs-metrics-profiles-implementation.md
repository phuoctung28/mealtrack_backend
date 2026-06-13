# Sentry Logs Metrics Profiles Implementation

Date: 2026-06-13

## Summary

Implemented the Sentry Logs, operational metrics, and explicit profile-session configuration extension on top of the provider-neutral observability connector.

## Changes

- Added Sentry settings for `SENTRY_ENABLE_LOGS`, `SENTRY_ENABLE_METRICS`, `SENTRY_PROFILE_SESSION_SAMPLE_RATE`, and `SENTRY_PROFILE_LIFECYCLE`.
- Extended `src.infra.monitoring` with provider-neutral structured log and metric facade calls.
- Added no-op connector support so disabled observability remains safe.
- Routed Sentry Logs through `sentry_sdk.logger` and metrics through `sentry_sdk.metrics`.
- Added scalar allowlist filtering for log and metric attributes.
- Updated `.env.example`, external services docs, architecture docs, troubleshooting, roadmap, and plan statuses.

## Verification

- `pytest tests/unit/infra/monitoring -q` passed: 17 passed.
- `pytest tests/unit/api/middleware/test_request_logger.py tests/unit/cron/test_email_cron.py tests/unit/cron/test_push_cron.py tests/unit/infra/services/test_affiliate_outbox_dispatch_service.py -q` passed: 24 passed, 1 warning.
- `rg "import sentry_sdk|sentry_sdk\\." src` only matched `src/infra/monitoring/sentry.py`.
- `mypy src/infra/monitoring src/infra/services/affiliate_outbox_dispatch_service.py` passed.
- `ruff check src/infra/monitoring src/infra/config/settings.py tests/unit/infra/monitoring` passed.
- `pytest -q` passed: 1608 passed, 3 skipped, 14 warnings.

## Known Unrelated Repo-Wide Gates

- `ruff check src tests` still fails with 1963 existing unrelated lint findings.
- `mypy src` still fails with 723 existing unrelated type findings.

## Unresolved Questions

None.

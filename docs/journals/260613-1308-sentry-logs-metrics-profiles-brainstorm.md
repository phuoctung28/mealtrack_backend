---
date: 2026-06-13
topic: sentry logs metrics profiles brainstorm
type: journal
---

# Sentry Logs Metrics Profiles Brainstorm

## Context

After completing the Sentry observability connector abstraction, user clarified that Sentry Logs must be enabled so the team can use Sentry Logs, metrics, and profiles.

## What Happened

- Scouted current connector, settings, docs, prior plan, and local SDK capabilities.
- Verified `enable_logs` is currently absent and local SDK default is `enable_logs=False`.
- Verified local SDK exposes metrics support and profile session settings.
- Checked current Sentry docs for Logs, Metrics, and Profiling.
- Recommended extending the existing facade rather than letting runtime code import `sentry_sdk.logger` or `sentry_sdk.metrics`.
- Wrote brainstorm report: `plans/reports/260613-1308-sentry-logs-metrics-profiles-brainstorm.md`.
- Created TDD plan: `plans/260613-1308-sentry-logs-metrics-profiles/plan.md`.

## Decisions

- Preserve connector abstraction.
- Add configurable Sentry Logs with `SENTRY_ENABLE_LOGS`.
- Add provider-neutral logs and metrics facade methods.
- Keep metrics operational only; do not replace product analytics.
- Keep log and metric attributes allowlisted and scalar.
- Keep profile sampling controlled by environment settings.

## Next

Run `/ck:cook thoroughly plans/260613-1308-sentry-logs-metrics-profiles/plan.md` when ready to implement.

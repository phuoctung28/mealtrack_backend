---
phase: 4
title: "Documentation and Verification"
status: completed
effort: "small"
---

# Phase 4: Documentation and Verification

## Context Links

- Plan: `plans/260613-1308-sentry-logs-metrics-profiles/plan.md`
- External services doc: `docs/external-services.md`
- Architecture doc: `docs/system-architecture.md`
- Troubleshooting doc: `docs/troubleshooting.md`
- Roadmap: `docs/project-roadmap.md`

## Overview

Priority: P2  
Status: Completed

Update docs and run final verification gates after implementation.

## Requirements

- Docs explain:
  - Sentry Logs require `SENTRY_ENABLE_LOGS`.
  - Python `LoggingIntegration` error events are different from Sentry Logs.
  - Metrics use facade methods and are operational only.
  - Profiling has sampling controls.
  - Privacy and cardinality rules.
- Roadmap records this connector extension.
- Verification commands are run and recorded in final handoff.

## Architecture

Docs should reinforce connector ownership:

```text
Application/runtime code -> observability facade -> Sentry connector -> Sentry SDK
```

## Related Code Files

Modify:

- `docs/external-services.md`
- `docs/system-architecture.md`
- `docs/troubleshooting.md`
- `docs/project-roadmap.md`

## Implementation Steps

1. Update `docs/external-services.md` Sentry section with logs, metrics, profiles, config, and privacy notes.
2. Update architecture doc if facade API changed meaningfully.
3. Update troubleshooting with logs/metrics verification steps.
4. Update roadmap completed phase after code is implemented.
5. Run focused gates:
   - `pytest tests/unit/infra/monitoring -q`
   - `rg "import sentry_sdk|sentry_sdk\\." src`
   - `mypy src/infra/monitoring src/infra/services/affiliate_outbox_dispatch_service.py`
   - `ruff check src/infra/monitoring src/infra/config/settings.py tests/unit/infra/monitoring`
6. Run full test suite:
   - `pytest`
7. Run repo-wide gates and report existing unrelated failures if they remain.

## Todo List

- [x] Update external services doc.
- [x] Update architecture/troubleshooting docs.
- [x] Update roadmap.
- [x] Run focused gates.
- [x] Run full pytest.
- [x] Record repo-wide lint/type status.

## Success Criteria

- Docs match implemented behavior.
- Full pytest passes.
- Source scan confirms Sentry SDK isolation.
- No unrelated code churn.

## Risk Assessment

- Repo-wide lint/type gates have known unrelated debt. Do not mass-fix unrelated files during this plan.

## Security Considerations

- Docs must explicitly say Sentry Logs/metrics cannot include PII, raw request data, provider payloads, or secrets.

## Next Steps

Handoff to `/ck:cook` for implementation after user approval.

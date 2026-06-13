---
phase: 5
title: "Documentation and Verification"
status: completed
priority: P2
effort: "4-6h"
dependencies: [1, 2, 3, 4]
---

# Phase 5: Documentation and Verification

## Context Links

- Audit: `plans/reports/260613-1313-application-logging-strategy-audit.md`
- External services doc: `docs/external-services.md`
- System architecture doc: `docs/system-architecture.md`
- Troubleshooting doc: `docs/troubleshooting.md`
- Project roadmap: `docs/project-roadmap.md`
- Related completed plan: `plans/260613-1308-sentry-logs-metrics-profiles/plan.md`

## Overview

Update docs after behavior is implemented, run focused and release gates, and
document how the cleanup hardens the completed Sentry Logs/Metrics/Profile work.

## Requirements

Functional:

- Docs define INFO/WARNING/ERROR/CRITICAL production rules.
- Docs state DEBUG is local/dev diagnostic only.
- Docs describe privacy/cardinality rules for logs, Sentry context, and metrics.
- Docs explain what stays out of logs: emails, raw image URLs, auth data, raw AI
  responses, request bodies, provider payloads, secrets.
- Roadmap/changelog records the logging hardening if this implementation ships.
- Cross-plan note is updated after completion if future logging-ingestion plans
  appear.

Non-functional:

- Docs must match actual code.
- Do not overpromise full structured logging or Sentry alert automation.
- Report any existing unrelated lint/type/test failures honestly.

## Architecture

Docs should present the signal split:

```text
logs = operational timeline
Sentry issues = error investigation
metrics = aggregate alert/trend signal
audit events = durable business history
```

## Related Code Files

Modify:

- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/external-services.md`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/system-architecture.md`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/troubleshooting.md`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/project-roadmap.md`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/plans/260613-1308-sentry-logs-metrics-profiles/plan.md` after this plan completes

## Key Insights

- Existing Sentry docs already forbid emails, food payloads, raw image URLs,
  provider payloads, and secrets.
- The completed Sentry Logs plan makes this cleanup more urgent because richer
  log ingestion increases the blast radius of unsafe log content.
- Repo-wide gates may expose unrelated existing debt; do not mass-fix unrelated
  files during this plan.

## Implementation Steps

### Tests Before

1. Re-run focused test suite from phases 1-4 before docs.
2. Run source scans for forbidden current patterns.

### Refactor

1. Update `docs/external-services.md` Sentry/logging section:
   - production severity table.
   - Sentry Logs vs Python `LoggingIntegration`.
   - privacy/cardinality policy.
2. Update `docs/system-architecture.md` observability/logging boundary:
   - API owns request logs.
   - infra owns provider/connector logs.
   - domain remains provider-neutral.
3. Update `docs/troubleshooting.md`:
   - how to inspect missing Sentry events.
   - how to check log severity and redaction.
   - relevant `rg` commands.
4. Update `docs/project-roadmap.md` after implementation ships.
5. If all gates pass, leave a short implementation note in the handoff that the
   completed Sentry Logs/Metrics/Profile work is now safer to operate.

### Tests After

1. Run all focused gates.
2. Run release gates.
3. Record any not-run or unrelated failures in implementation handoff.

### Regression Gate

Run:

```bash
pytest tests/unit/api/middleware/test_request_logger.py -q
pytest tests/unit/infra/monitoring -q
pytest tests/unit/infra/adapters/test_logging_redaction.py tests/unit/app/handlers/command_handlers/test_upload_meal_image_immediately_logging.py tests/unit/infra/adapters/test_resend_email_adapter_logging.py tests/unit/api/routes/test_revenuecat_webhook_logging.py -q
pytest tests/unit/api/test_api_main_firebase_and_lifespan.py -q
rg "import sentry_sdk|sentry_sdk\\." src
rg "content\\[:500\\]|Email sent to|Failed to send email to|Cloudinary URL|https://res.cloudinary.com" src tests
ruff check src tests
mypy src
pytest
```

## Success Criteria

- [ ] Docs match implemented severity and privacy policy.
- [ ] Focused tests pass.
- [ ] Sentry SDK isolation scan passes.
- [ ] Forbidden raw-content scan has no production-code hits.
- [ ] Release gates pass or unrelated pre-existing failures are documented.
- [ ] Completed Sentry Logs/Metrics/Profile work remains compatible with cleanup.

## Risk Assessment

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Docs drift from code | Operational confusion | Update docs after behavior changes |
| Sentry Logs already exist in worktree | Wider log leakage | Prioritize P0/P1 redaction before broader log use |
| Repo-wide gates fail for unrelated worktree changes | Scope creep | Report honestly, do not mass-fix unrelated files |

## Security Considerations

- Docs must continue to reject request bodies, auth headers, Firebase claims,
  emails, food payloads, raw image URLs, raw provider payloads, and secrets.
- Metrics docs must forbid high-cardinality tags such as user IDs and image IDs.

## Next Steps

After completion, consider only if new operational needs appear:

```bash
/ck:plan --tdd broader-structured-logging-rollout
```

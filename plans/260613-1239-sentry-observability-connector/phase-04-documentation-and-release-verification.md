---
phase: 4
title: "Documentation and Release Verification"
status: completed
priority: P2
effort: "3-5h"
dependencies: [1, 2, 3]
---

# Phase 4: Documentation and Release Verification

## Context Links

- Plan: `plans/260613-1239-sentry-observability-connector/plan.md`
- External services doc: `docs/external-services.md`
- System architecture doc: `docs/system-architecture.md`
- Project roadmap: `docs/project-roadmap.md`
- Code standards: `docs/code-standards.md`

## Overview

Update docs to describe Sentry as a connector-backed observability provider, document privacy rules, and run final verification gates.

## Key Insights

- Existing docs already say Sentry degrades to local logging.
- User asked to include alert/dashboard setup as well; safest first pass is a documented operations checklist.
- Sentry API automation should be deferred unless a token and ownership model are explicitly provided.

## Requirements

Functional:
- Update external services docs with new facade and env vars.
- Update architecture docs with monitoring boundary.
- Update roadmap/changelog style docs only if this implementation changes status.
- Document the Sentry event contract: what is sent, what is never sent, and the allowed context keys.
- Document alert/dashboard checklist.
- Document privacy allowlist/denylist.

Non-functional:
- Docs must match actual implementation.
- No secrets or DSNs in docs.
- Any pre-existing doc validation warnings should be called out separately.

## Architecture

Docs should describe the boundary this way:

```text
Application/runtime code -> observability facade -> Sentry connector -> Sentry SDK
```

Sentry setup is operational configuration, not product logic.

## Related Code Files

- Modify: `docs/external-services.md`
- Modify: `docs/system-architecture.md`
- Modify: `docs/project-roadmap.md`
- Modify if useful: `docs/troubleshooting.md`
- Modify if useful: `docs/codebase-summary.md`

## Implementation Steps

### Tests Before

1. Run focused tests from phases 1-3 before docs to confirm behavior is stable.
2. Run `rg "import sentry_sdk|sentry_sdk\\." src`.

### Refactor

1. Update `docs/external-services.md`:
   - Sentry purpose
   - connector facade
   - env vars
   - graceful degradation
   - event contract
   - privacy policy
2. Update `docs/system-architecture.md`:
   - monitoring boundary in infrastructure layer
   - request context ownership
3. Update `docs/project-roadmap.md` or changelog equivalent:
   - mark abstraction work or add completed technical-debt item.
4. Add alert/dashboard checklist:
   - new high-severity errors
   - repeated cron failures
   - affiliate permanent failures
   - 5xx rate by route
   - slowest API transactions
   - top exception classes
5. Explicitly defer Sentry API automation unless user provides token/ownership.

### Tests After

1. Run focused unit tests.
2. Run lint/type/test release gates if time permits.
3. Document any not-run gate in final implementation summary.

### Regression Gate

Run:

```bash
pytest tests/unit/infra/monitoring tests/unit/api/middleware/test_request_logger.py tests/unit/cron/test_email_cron.py tests/unit/cron/test_push_cron.py tests/unit/infra/services/test_affiliate_outbox_dispatch_service.py -q
pytest tests/unit/api/test_api_main_firebase_and_lifespan.py tests/unit/api/test_exceptions_unexpected.py -q
ruff check src tests
mypy src
pytest
```

## Success Criteria

- [ ] Docs explain observability facade and Sentry connector ownership.
- [ ] Docs include env vars and privacy constraints.
- [ ] Docs include alert/dashboard checklist.
- [ ] Direct SDK import search is clean.
- [ ] Focused tests pass.
- [ ] Broader gates either pass or are reported honestly.

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Docs overpromise automated Sentry operations | Future confusion | Checklist only unless automation is implemented |
| Docs drift from code | Misleading ops guide | Update after implementation, not before behavior exists |
| Full `pytest` is slow/flaky | Delayed ship | Run focused gates first; report broad gate status separately |

## Security Considerations

- Never document real DSNs, tokens, or secrets.
- Privacy policy must explicitly reject request bodies, auth headers, emails, tokens, food payloads, raw image URLs, and service credentials.

## Next Steps

- Future optional phase: Sentry API-managed alerts/dashboards after user provides token, organization slug, and project slug.

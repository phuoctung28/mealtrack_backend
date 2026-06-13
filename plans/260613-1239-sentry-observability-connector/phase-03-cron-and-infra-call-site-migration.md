---
phase: 3
title: "Cron and Infra Call Site Migration"
status: completed
priority: P1
effort: "4-6h"
dependencies: [1, 2]
---

# Phase 3: Cron and Infra Call Site Migration

## Context Links

- Plan: `plans/260613-1239-sentry-observability-connector/plan.md`
- Phase 2: `phase-02-sentry-connector-and-api-context-wiring.md`
- Email cron: `src/cron/email.py`
- Push cron: `src/cron/push.py`
- Affiliate cron: `src/cron/affiliate_outbox.py`
- Affiliate dispatch service: `src/infra/services/affiliate_outbox_dispatch_service.py`

## Overview

Migrate cron entry points and infra services away from direct `sentry_sdk` imports. Preserve existing flush and alert semantics through the facade.

## Key Insights

- Cron jobs currently call `initialize_sentry()` and `sentry_sdk.flush(timeout=5)`.
- Affiliate outbox dispatcher captures a permanent-failure Sentry message.
- Existing cron tests patch `sentry_sdk.flush`; they must move to facade patching.
- Operational paths should degrade: monitoring failure must not prevent cron cleanup or DB disposal.

## Requirements

Functional:
- Replace direct SDK imports in cron files with observability facade calls.
- Replace permanent-failure `capture_message()` in affiliate dispatch service.
- Send only affiliate permanent-failure metadata: row ID, event ID, event type, and attempt count if available.
- Preserve early-exit warm-up failure flush behavior.
- Preserve final flush after successful cron work.
- Preserve affiliate cron re-raise behavior after capture/logging.

Non-functional:
- No `sentry_sdk` import outside connector.
- Cron cleanup still disposes async engine.
- Tests remain network-free.

## Architecture

```text
cron.run()
  logging.basicConfig(...)
  initialize_observability()
  try work
  finally / early exit: flush_observability(timeout=5)

affiliate_outbox_dispatch_service
  capture_message("Affiliate outbox row permanently failed...", level="error", context=safe ids)
```

Affiliate context is limited to `row_id`, `event_id`, `event_type`, and `attempt_count` if available. Do not attach payload contents.

## Related Code Files

- Modify: `src/cron/email.py`
- Modify: `src/cron/push.py`
- Modify: `src/cron/affiliate_outbox.py`
- Modify: `src/infra/services/affiliate_outbox_dispatch_service.py`
- Modify: `tests/unit/cron/test_email_cron.py`
- Modify: `tests/unit/cron/test_push_cron.py`
- Modify: `tests/unit/infra/services/test_affiliate_outbox_dispatch_service.py`
- Add if missing: `tests/unit/cron/test_affiliate_outbox_cron.py`

## Implementation Steps

### Tests Before

1. Update cron tests first to expect facade `initialize_observability()` and `flush()`.
2. Add/adjust affiliate dispatch test to patch facade `capture_message()`.
3. Add/adjust affiliate dispatch test to assert payload contents are not forwarded to Sentry context.
4. Add search-based test or architecture assertion if local pattern exists; otherwise include command gate in phase verification.

### Refactor

1. Replace `from src.infra.monitoring.sentry import initialize_sentry` with facade import.
2. Replace `import sentry_sdk` usage:
   - `sentry_sdk.flush(timeout=5)` -> `flush_observability(timeout=5)`
   - `sentry_sdk.capture_exception()` -> `capture_exception(exc)` or rely on logger then flush; use explicit capture where caught and re-raised.
   - `sentry_sdk.capture_message(...)` -> `capture_message(..., level="error", context=safe_context)`
3. Keep logging semantics unchanged.
4. Keep DB disposal behavior unchanged.

### Tests After

1. Run cron tests.
2. Run affiliate dispatch tests.
3. Run `rg "import sentry_sdk|sentry_sdk\\." src` and confirm only connector remains.

### Regression Gate

Run:

```bash
pytest tests/unit/cron/test_email_cron.py tests/unit/cron/test_push_cron.py tests/unit/infra/services/test_affiliate_outbox_dispatch_service.py -q
rg "import sentry_sdk|sentry_sdk\\." src
```

## Success Criteria

- [ ] Cron entry points use facade init/flush.
- [ ] Affiliate permanent failure uses facade capture.
- [ ] Direct SDK imports are gone outside connector.
- [ ] Cron tests still prove warm-up failure early exits cleanly.
- [ ] Async engine disposal remains covered.

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Cron exits before events flush | Lost operational events | Preserve timeout=5 flush on early exit/final path |
| Affiliate failure context leaks user data | Privacy issue | Include row id/event type/event id only |
| Replacing capture changes exception propagation | Cron behavior regression | Keep existing catch/log/re-raise behavior |

## Security Considerations

- Do not attach affiliate payload contents.
- Do not include HMAC secrets, API base URLs with credentials, or user emails.

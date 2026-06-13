---
phase: 1
title: "Regression Guards"
status: completed
priority: P1
effort: "4-6h"
dependencies: []
---

# Phase 1: Regression Guards

## Context Links

- Plan: `plans/260613-1319-production-logging-severity-privacy-cleanup/plan.md`
- Audit: `plans/reports/260613-1313-application-logging-strategy-audit.md`
- Existing request tests: `tests/unit/api/middleware/test_request_logger.py`
- Existing monitoring tests: `tests/unit/infra/monitoring/`

## Overview

Create failing tests and search-based guardrails before any logging behavior
changes. This phase locks the desired production contract: no raw sensitive
content in representative logs, no Sentry SDK leakage, and clear severity
expectations.

## Requirements

Functional:

- Add tests for log redaction on the highest-risk call sites.
- Add request severity tests for expected client errors, slow responses, and 5xx.
- Add a test or command gate that confirms direct `sentry_sdk` imports remain
  isolated to `src/infra/monitoring/sentry.py`.
- Establish helper test assertions for "does not contain email/url/raw AI/auth".

Non-functional:

- Tests must not call real Sentry, Resend, Cloudinary, Firebase, or Gemini.
- Tests must use pytest + mocks per repo standards.
- No production code changes until tests fail for the intended reasons.

## Architecture

Testing strategy:

```text
caplog / monkeypatch / fake adapters
        |
        v
representative logging call sites
        |
        v
assert safe operational metadata only
```

Use tests to encode policy. Do not add a new logging framework.

## Related Code Files

Create:

- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/adapters/test_logging_redaction.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/app/handlers/command_handlers/test_upload_meal_image_immediately_logging.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/adapters/test_resend_email_adapter_logging.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/routes/test_revenuecat_webhook_logging.py`

Modify:

- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/middleware/test_request_logger.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/monitoring/test_sentry_connector.py`

## Key Insights

- Existing request logger tests currently expect 4xx as WARNING; phase 2 will
  intentionally change that expectation.
- Existing Sentry connector tests already prove allowlisted context filtering;
  use that pattern for log redaction assertions.
- Avoid brittle exact-message tests except for known forbidden substrings.

## Implementation Steps

### Tests Before

1. Add request middleware tests:
   - 200 response logs INFO.
   - 404 response logs INFO, not WARNING.
   - 401/403 response logs INFO, not WARNING.
   - 429 response logs WARNING.
   - slow 200 response logs WARNING.
   - unhandled exception/500 response logs ERROR.
2. Add redaction tests for:
   - AI JSON extraction failure does not log raw content snippet.
   - Upload flow logs `image_id` and elapsed time, not raw `image_url`.
   - Email send logs provider/message ID or error type, not recipient email or subject.
   - RevenueCat missing-user path does not log aliases/raw provider IDs wholesale.
   - Cloudinary image store debug/error logs do not include raw delivery URLs.
3. Add import isolation gate:
   - either pytest shell-like assertion or plan release gate:
     `rg "import sentry_sdk|sentry_sdk\\." src`.
4. Confirm the new tests fail before production code changes.

### Refactor

No production refactor in this phase except small test helpers if needed.

### Tests After

1. Run the newly added tests and record expected failures.
2. Ensure failures are policy failures, not test setup errors.

### Regression Gate

Run:

```bash
pytest tests/unit/api/middleware/test_request_logger.py -q
pytest tests/unit/infra/monitoring -q
pytest tests/unit/infra/adapters/test_logging_redaction.py tests/unit/app/handlers/command_handlers/test_upload_meal_image_immediately_logging.py tests/unit/infra/adapters/test_resend_email_adapter_logging.py -q
```

## Success Criteria

- [ ] Tests encode severity matrix before code changes.
- [ ] Tests encode P0/P1 sensitive log redaction before code changes.
- [ ] New tests fail only for known current behavior gaps.
- [ ] No production logging implementation changed in this phase.

## Risk Assessment

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Tests overfit exact message text | Refactor friction | Assert levels and forbidden substrings first |
| Tests require external SDK behavior | Flaky/no network | Use fakes/mocks and caplog |
| Too many guardrails at once | Slows implementation | Limit to P0/P1 hotspots |

## Security Considerations

- Test fixtures may contain fake secrets/URLs/emails, but they must never come
  from real `.env` values.
- Redaction assertions should cover representative patterns:
  `@`, `http://`, `https://`, `Bearer`, `content[:500]` style output.

## Next Steps

Proceed to request severity policy after guard tests exist.

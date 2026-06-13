---
phase: 3
title: "Sensitive Log Redaction"
status: completed
priority: P1
effort: "1-1.5d"
dependencies: [1, 2]
---

# Phase 3: Sensitive Log Redaction

## Context Links

- Audit: `plans/reports/260613-1313-application-logging-strategy-audit.md`
- AI parser: `src/infra/adapters/vision_ai_service.py`
- Upload flow: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Email adapter: `src/infra/adapters/resend_email_adapter.py`
- Cloudinary adapter: `src/infra/adapters/cloudinary_image_store.py`
- RevenueCat webhooks: `src/api/routes/v1/webhooks.py`

## Overview

Remove P0/P1 sensitive or noisy content from representative production logs.
Keep operational context useful by replacing raw values with safe IDs, provider
names, error types, elapsed times, and counts.

## Requirements

Functional:

- AI parse failures log parser stage, content length, and error type, not raw AI
  response snippets.
- Upload flow logs `image_id`, result, elapsed, and error type, not raw image URL.
- Email adapter logs provider/result/message ID/error type, not recipient email or
  subject.
- Cloudinary adapter does not log raw Cloudinary URLs.
- RevenueCat webhook logs avoid raw alias lists and unnecessary provider
  identifiers; keep event type and safe internal event/user context.
- High-risk f-string logger calls in these files become lazy `%s` logging calls.

Non-functional:

- Do not change public API responses unless existing error text leaks raw URL;
  if response text leaks URL, replace with generic message and safe details.
- Do not alter Cloudinary upload, email send, AI analysis, or RevenueCat business
  behavior.
- Keep domain layer free of monitoring imports.

## Architecture

No new logging framework. Use local helper functions only if they remove real
duplication:

```text
call site catches/handles error
        |
        v
logger.<level>("operation failed: provider=%s error_type=%s", provider, type(exc).__name__)
```

Use the existing observability filters only for Sentry/facade attributes. Do not
make app code import Sentry directly.

## Related Code Files

Modify:

- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/adapters/vision_ai_service.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/adapters/resend_email_adapter.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/adapters/cloudinary_image_store.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/webhooks.py`

Create/modify tests from phase 1:

- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/adapters/test_logging_redaction.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/app/handlers/command_handlers/test_upload_meal_image_immediately_logging.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/adapters/test_resend_email_adapter_logging.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/routes/test_revenuecat_webhook_logging.py`

## Key Insights

- Current code logs `content[:500]` for AI response parse failures.
- Upload flow logs raw `image_url` on success and invalid URL paths.
- Resend adapter logs `to` and `subject`.
- Cloudinary adapter debug logs raw Cloudinary URLs and fallback URLs.
- RevenueCat route logs provider IDs and aliases in a missing-user error path.

## Implementation Steps

### Tests Before

1. Use caplog tests from phase 1 as the failing contract.
2. Add exact forbidden-substring assertions:
   - fake email address.
   - fake subject.
   - fake `https://res.cloudinary.com/...` URL.
   - fake raw AI JSON/body text.
   - fake `Bearer`.
   - fake RevenueCat aliases list.
3. Add positive assertions that safe context remains:
   - `image_id`
   - operation name
   - provider name
   - error type
   - elapsed time or content length where useful.

### Refactor

1. `vision_ai_service.py`:
   - Replace raw content snippet logs with safe metadata:
     content length, parser step, brace counts if helpful, error type.
   - Keep user-facing exception messages generic.
2. `upload_meal_image_immediately_command_handler.py`:
   - Remove raw `image_url` from logs.
   - Replace invalid URL runtime error message with generic text if it would
     surface the raw URL.
   - Keep `image_id` and elapsed time.
3. `resend_email_adapter.py`:
   - Remove `to` and `subject` from logs.
   - Log provider, result, message ID if available, and error type.
4. `cloudinary_image_store.py`:
   - Remove raw delivery/fallback URLs from debug logs.
   - Keep `image_id`, public ID, format, status code, and error type.
5. `webhooks.py`:
   - Keep invalid auth WARNING.
   - Reduce missing-user ERROR to event type and internal-safe event ID/provider
     context. Avoid raw aliases list in log message.
6. Convert touched high-risk f-string logger calls to lazy logging args.

### Tests After

1. Run the redaction tests.
2. Run focused tests for affected adapters/routes.
3. Run Sentry import isolation scan.

### Regression Gate

Run:

```bash
pytest tests/unit/infra/adapters/test_logging_redaction.py tests/unit/app/handlers/command_handlers/test_upload_meal_image_immediately_logging.py tests/unit/infra/adapters/test_resend_email_adapter_logging.py tests/unit/api/routes/test_revenuecat_webhook_logging.py -q
pytest tests/unit/infra/monitoring -q
rg "import sentry_sdk|sentry_sdk\\." src
rg "content\\[:500\\]|Email sent to|Failed to send email to|Cloudinary URL|url=%s|url=\\{image_url\\}" src
```

## Success Criteria

- [ ] Raw AI response snippets no longer appear in logs.
- [ ] Raw image URLs no longer appear in logs.
- [ ] Email recipient and subject no longer appear in logs.
- [ ] RevenueCat missing-user logs avoid raw alias/provider payload sprawl.
- [ ] Touched logs preserve enough metadata for debugging.
- [ ] No public API success response shape changes.

## Risk Assessment

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Over-redaction hurts debugging | Slower incident triage | Keep safe IDs, error type, provider, operation |
| Error response text changes mobile expectations | Client regression | Change only raw-URL leak paths; keep codes/status stable |
| Tests miss an adjacent leak | Privacy gap | Add search gates and representative caplog tests |

## Security Considerations

- This phase directly reduces exposure of PII/provider data in production logs.
- Do not add hashes for emails unless needed; a stable hash can still become an
  identifier. Prefer no email in logs.

## Next Steps

Proceed to CRITICAL/startup boundary policy.

---
phase: 2
title: "Request Severity Policy"
status: completed
priority: P1
effort: "4-6h"
dependencies: [1]
---

# Phase 2: Request Severity Policy

## Context Links

- Request middleware: `src/api/middleware/request_logger.py`
- Request tests: `tests/unit/api/middleware/test_request_logger.py`
- Sentry docs: `docs/external-services.md`
- Audit: `plans/reports/260613-1313-application-logging-strategy-audit.md`

## Overview

Change request logging from "all 4xx are WARNING" to a production taxonomy:
expected client errors are INFO, abuse/boundary failures and slow responses are
WARNING, 5xx/unhandled failures are ERROR.

## Requirements

Functional:

- 2xx/3xx request-response logs stay INFO.
- Expected 400/401/403/404 responses log INFO.
- 429 rate-limit responses log WARNING.
- Slow responses log WARNING even with 2xx status.
- 5xx responses log ERROR.
- Exceptions still log `[ERR-...]` at ERROR.
- Request body, Authorization header, and raw query/body data are never logged.

Non-functional:

- Keep pure ASGI middleware; do not introduce `BaseHTTPMiddleware`.
- Keep `X-Request-ID` and `X-Response-Time` behavior stable.
- Keep Sentry request context allowlisted.

## Architecture

Policy belongs in `RequestLoggerMiddleware._log_response`.

Suggested helper:

```python
def _response_log_level(status_code: int, elapsed: float) -> int:
    if status_code >= 500:
        return logging.ERROR
    if elapsed > SLOW_REQUEST_THRESHOLD_SECONDS or status_code == 429:
        return logging.WARNING
    return logging.INFO
```

Do not make this a new service/class.

## Related Code Files

Modify:

- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/middleware/request_logger.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/middleware/test_request_logger.py`

## Key Insights

- `RequestLoggerMiddleware` currently sets WARNING for all `status_code >= 400`.
- Sentry docs already say expected 4xx should not become Sentry issues.
- Keeping 429 as WARNING preserves operational signal for abuse/rate-limit spikes.

## Implementation Steps

### Tests Before

1. Update `test_logs_warning_on_4xx` into separate tests:
   - `test_logs_info_on_expected_404`.
   - `test_logs_info_on_expected_401_or_403`.
   - `test_logs_warning_on_429`.
2. Keep `test_warns_on_slow_request`.
3. Keep or add `test_logs_error_on_exception`.
4. Add assertion that Authorization header is not present in any request log.

### Refactor

1. Add a small private helper for response log-level selection, or keep inline if
   simpler.
2. Change 4xx logic:
   - `>=500` -> ERROR.
   - `429` -> WARNING.
   - slow -> WARNING.
   - other 4xx -> INFO.
3. Convert request/response/error log calls to lazy logging args where practical.
4. Keep request ID format and headers unchanged.

### Tests After

1. Run request logger tests.
2. Run API exception tests if touched.

### Regression Gate

Run:

```bash
pytest tests/unit/api/middleware/test_request_logger.py -q
pytest tests/unit/api/test_exceptions_unexpected.py -q
```

## Success Criteria

- [ ] Expected 4xx no longer creates WARNING log records.
- [ ] 429 and slow responses still create WARNING.
- [ ] 5xx/unhandled failures still create ERROR.
- [ ] Request ID and response-time headers unchanged.
- [ ] No request body/auth header logging introduced.

## Risk Assessment

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Downgrading all 4xx hides abuse | Missed attack signal | Keep 429 and webhook auth boundary warnings |
| Sentry issue volume changes unexpectedly | Alert drift | Sentry event contract already excludes expected 4xx |
| Helper over-abstracts simple policy | Extra code | Keep helper tiny/private or inline |

## Security Considerations

- Do not log auth headers, cookies, Firebase claims, request bodies, or raw query
  strings.
- Use route/path already present; future improvement may normalize route templates.

## Next Steps

Proceed to P0/P1 sensitive log redaction.

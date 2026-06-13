---
phase: 4
title: "Critical Startup Boundaries"
status: completed
priority: P2
effort: "4-6h"
dependencies: [1, 2, 3]
---

# Phase 4: Critical Startup Boundaries

## Context Links

- App startup: `src/api/main.py`
- Health route: `src/api/routes/v1/health.py`
- Settings: `src/infra/config/settings.py`
- Existing API startup tests: `tests/unit/api/test_api_main_firebase_and_lifespan.py`
- Audit: `plans/reports/260613-1313-application-logging-strategy-audit.md`

## Overview

Introduce a narrow CRITICAL policy for page-worthy core failures. Do not turn
optional dependency degradation into alert noise.

## Requirements

Functional:

- Required startup failures that abort app serving may log CRITICAL.
- Optional/degraded startup paths remain WARNING or ERROR:
  - Redis unavailable when cache failure is allowed.
  - PostHog missing/failed.
  - Gemini cache warmup failed but uncached calls continue.
  - Email disabled/misconfigured.
- Firebase init failure that aborts startup may log CRITICAL.
- DB warm failure remains WARNING unless production readiness policy explicitly
  says DB warm failure makes service unusable.
- Request-time unhandled 5xx remains ERROR, not CRITICAL.

Non-functional:

- No alert spam. CRITICAL must mean "page-worthy".
- No change to startup control flow unless tests prove current behavior already
  aborts.
- Keep config surface minimal; do not add a new alerting framework.

## Architecture

CRITICAL is a severity decision at the boundary where the service decides it
cannot run.

```text
startup/lifespan required dependency fails
        |
        v
logger.critical(..., exc_info=True) if process will fail/raise
```

Do not place CRITICAL in ordinary adapter catch blocks.

## Related Code Files

Modify:

- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/main.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/test_api_main_firebase_and_lifespan.py`

Optional if existing health tests support it:

- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/health.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/test_health.py`

## Key Insights

- Current code has zero `logger.critical`/`logger.fatal` usage.
- Cache initialization logs ERROR then raises only when `FAIL_ON_CACHE_ERROR=true`;
  that may be CRITICAL only in fail-fast configuration.
- DB warm failure currently logs WARNING and continues.

## Implementation Steps

### Tests Before

1. Add startup tests with caplog:
   - Firebase initialization failure that aborts startup logs CRITICAL.
   - Cache initialization failure with `FAIL_ON_CACHE_ERROR=true` logs CRITICAL
     before raising.
   - Cache initialization failure with `FAIL_ON_CACHE_ERROR=false` does not log
     CRITICAL.
   - PostHog/Gemini optional failures do not log CRITICAL.
2. If health/readiness route already has dependency checks, add test for
   CRITICAL only when core health fails and endpoint signals unusable.

### Refactor

1. Replace only page-worthy aborting startup `logger.error(...)` calls with
   `logger.critical(..., exc_info=True)` where appropriate.
2. Keep optional dependency degradation at WARNING/ERROR.
3. Convert touched f-string warning logs in startup to lazy `%s` args.
4. Do not add `logger.fatal`; use `logger.critical`.

### Tests After

1. Run startup/lifespan tests.
2. Run request middleware tests to prove request-time ERROR behavior unchanged.
3. Search for CRITICAL/fatal usage.

### Regression Gate

Run:

```bash
pytest tests/unit/api/test_api_main_firebase_and_lifespan.py tests/unit/api/middleware/test_request_logger.py -q
rg "logger\\.(critical|fatal)|logging\\.(CRITICAL|FATAL)" src tests
```

## Success Criteria

- [ ] CRITICAL appears only in approved startup/readiness failure paths.
- [ ] Optional dependency failures do not page.
- [ ] App startup behavior remains otherwise unchanged.
- [ ] Search confirms no `logger.fatal` usage.

## Risk Assessment

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Overusing CRITICAL creates alert fatigue | On-call noise | Only log CRITICAL on fail/raise paths |
| Underusing CRITICAL hides true outage | Missed page | Tests cover required dependency aborts |
| Startup tests are brittle | Flaky plan | Patch dependencies directly, no real external calls |

## Security Considerations

- Critical logs must not include service account JSON, env values, DSNs, or
  Firebase credential contents.
- Use exception type and stable message, not secret-bearing exception details if
  a provider includes config values.

## Next Steps

Proceed to docs and final verification.

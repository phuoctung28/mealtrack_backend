# Phase 01: Exception Boundary Relocation

## Context Links

- [Plan overview](./plan.md)
- [Architecture alignment guide](../../docs/architecture/async-cqrs-feature-alignment.md)
- [Scout report](./reports/architecture-alignment-scout-report.md)
- Current source: `src/api/exceptions.py`

## Overview

**Priority:** P1
**Status:** Planned

Move reusable MealTrack exception classes out of the API layer. Keep HTTP status
mapping and FastAPI `HTTPException` conversion in `src/api`.

## Key Insights

- App and infra currently import `src.api.exceptions`.
- These exception classes are not HTTP-specific, but their module ownership is.
- Import-linter is green because existing exceptions are effectively baseline
  debt, not because the direction is clean.

## Requirements

- Preserve public API error status codes and response shape.
- Do not introduce broad exception renames in API responses.
- Do not move FastAPI-specific helpers out of API.

## Architecture

Target ownership:

```text
src/domain or src/app exceptions -> API mapper -> HTTPException
```

`create_http_exception()` and `handle_exception()` stay in API. Reusable
application/domain exception classes move to a lower layer.

## Related Code Files

Modify:
- `src/api/exceptions.py`
- App/infra imports found by `rg "from src.api.exceptions import" src/app src/infra`
- `.importlinter`
- Targeted tests that import exceptions

Create:
- `src/domain/exceptions/base.py` or `src/app/exceptions.py` after ownership check

## Implementation Steps

1. Choose exception owner: domain for pure business exceptions, app if some
   errors are use-case/application specific.
2. Move `MealTrackException` and concrete subclasses.
3. Leave API-only HTTP mapping in `src/api/exceptions.py`.
4. Update app, infra, API, and tests to import from the new owner.
5. Remove matching `.importlinter` ignore lines.
6. Add a static test blocking non-API imports of `fastapi.HTTPException`.

## Todo List

- [ ] Pick target module.
- [ ] Move exception classes.
- [ ] Update imports.
- [ ] Shrink import-linter baselines.
- [ ] Add static guard.
- [ ] Run targeted route/handler tests.

## Success Criteria

- No `src/app` or `src/infra` file imports `src.api.exceptions`.
- HTTP error responses stay compatible.
- `lint-imports` remains green with fewer baselines.

## Risk Assessment

- Medium: many imports touch handler tests.
- Mitigation: mechanical import change plus targeted route/handler tests.

## Security Considerations

Exception payload shape must not start leaking internal stack traces, SQL errors,
tokens, or external provider raw responses.

## Next Steps

After this phase, Phase 2 can shrink direct app-to-infra imports without mixing
that work with error ownership.


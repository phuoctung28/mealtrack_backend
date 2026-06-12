# Phase 02: App-To-Infra Baseline Shrink

## Context Links

- [Plan overview](./plan.md)
- `.importlinter`
- `src/api/dependencies/event_bus.py`
- `src/infra/database/uow_async.py`

## Overview

**Priority:** P1
**Status:** Planned

Shrink the broad `src.app -> src.infra` import-linter baseline as feature areas
are touched. This is not a big-bang refactor.

## Key Insights

- `lint-imports` currently passes.
- Many app handlers still instantiate `AsyncUnitOfWork` or import infra models
  directly.
- Existing allowlist entries are transition debt and must not be copied into new
  features.

## Requirements

- Do not add new import-linter ignore lines for features.
- Keep public API behavior unchanged.
- Prefer ports and UoW injection over direct infrastructure imports.

## Architecture

Target flow:

```text
API composition root -> handler with ports/UoW factory -> domain service -> infra implementation
```

Application handlers should depend on `AsyncUnitOfWorkPort` or narrower ports.
Infrastructure implementations are wired in the API composition root.

## Related Code Files

Modify as slices are touched:
- `src/api/dependencies/event_bus.py`
- `src/app/handlers/**/*.py`
- `src/domain/ports/**/*.py`
- `src/infra/repositories/**/*.py`
- `.importlinter`

## Implementation Steps

1. Pick one feature slice from the touched work, not the whole app layer.
2. Replace handler direct infra imports with injected ports or UoW factory.
3. Move raw SQLAlchemy model queries from app handlers into repositories.
4. Update fakes/tests to match async port contracts.
5. Remove the corresponding `.importlinter` ignore lines.

## Todo List

- [ ] Select first migrated slice.
- [ ] Define or reuse needed port methods.
- [ ] Move infra query logic into repository.
- [ ] Update event-bus wiring.
- [ ] Update tests and fakes.
- [ ] Remove matching baselines.

## Success Criteria

- New features add no import-linter allowlist entries.
- Touched handlers do not import infra models/repositories directly.
- Domain isolation remains clean.

## Risk Assessment

- Medium: handler fakes can drift from runtime contracts.
- Mitigation: run handler tests plus `tests/unit/domain/ports/test_async_repository_contracts.py` when ports change.

## Security Considerations

Ownership checks must remain in the handler/repository path. Moving queries into
repositories must not widen cross-user reads.

## Next Steps

After each migrated slice, update the scout report or phase notes with the
ignore lines removed.


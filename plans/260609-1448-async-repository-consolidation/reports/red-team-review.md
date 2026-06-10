---
type: red-team-review
created: 2026-06-09 14:48
topic: async repository consolidation plan
status: complete
---

# Red-Team Review

## Summary

The approved phased async-only strategy is correct, but the plan can still fail if it treats "remove sync" as a grep cleanup. The dangerous parts are Alembic/runtime Base coupling, transaction ownership behavior changes, hidden route dependencies, and test fixtures that mask real async issues.

## Findings

### R1 - Deleting `config.py` Too Early Can Break ORM Base Imports

Many ORM models import `Base` from `src.infra.database.config`. If runtime sync config is removed, `Base` must move to a neutral module first or models/migrations break.

Mitigation:

- Introduce neutral declarative base module before deleting sync config.
- Update model imports and Alembic env deliberately.

### R2 - Repository Commit Removal Can Change Persisted Behavior

Sync repositories currently commit internally. Async repositories do not. If a caller depended on immediate commit semantics, moving to UoW commit-at-exit changes timing.

Mitigation:

- Convert callers to explicit UoW boundaries.
- Add behavior tests around manual meal save, notification token updates, food reference upserts, pending image queue writes, and pgvector cache writes.

### R3 - Pgvector Cache Error Handling Has a Known Failure Mode

Past pgvector/cache errors poisoned shared transactions. Async conversion cannot simply remove rollback behavior and assume UoW handles it.

Mitigation:

- Keep cache lookup failure behavior explicit: fallback to miss and ensure any failed DB transaction is recovered before subsequent writes.
- Test the exact failure path.

### R4 - Tests May Go Green While Runtime Is Still Sync

Current tests patch sync `SessionLocal`, `ScopedSession`, and wrappers. They may pass even if runtime still uses sync dependencies.

Mitigation:

- Add static architecture tests banning runtime sync DB imports.
- Remove async wrappers after async fixtures exist.

### R5 - Alembic May Still Need Sync Engine

Removing `psycopg2` and sync engine config before Alembic is migrated can break deployments.

Mitigation:

- Separate "runtime async-only" from "migration tooling async-only".
- Either migrate Alembic to async or isolate a migration-only sync config with no runtime imports.

## Decision

Proceed, but strengthen the plan:

- Add a dedicated Base/config split phase.
- Do not delete sync config until ORM/Alembic imports are settled.
- Make pgvector cache failure recovery a named acceptance criterion.
- Include static guard tests before final deletion.

## Unresolved Questions

None.

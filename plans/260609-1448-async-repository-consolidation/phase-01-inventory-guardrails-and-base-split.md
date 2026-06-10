---
phase: 1
title: "Inventory, Guardrails, and Base Split"
status: completed
priority: P1
effort: "2-3 days"
dependencies: []
---

# Phase 1: Inventory, Guardrails, and Base Split

## Overview

Create a precise migration inventory, add static guardrails, and split SQLAlchemy declarative `Base` away from runtime sync DB config before any sync config deletion.

## Requirements

- Functional: identify all sync DB runtime imports, sync repository consumers, internal repository commits, and sync test wrappers.
- Functional: create guard tests that fail on new runtime sync DB usage.
- Functional: move or alias declarative `Base` through a neutral module without breaking model registry or Alembic.
- Non-functional: no API behavior change.

## Architecture

Introduce a neutral database base module, for example `src/infra/database/base.py`, that owns `Base`. Existing sync and async config can import from it during transition. Models eventually import `Base` from the neutral module.

## Related Code Files

- Create: `src/infra/database/base.py`
- Create/Modify: `tests/architecture/test_async_db_runtime_boundaries.py`
- Modify: `src/infra/database/config.py`
- Modify: `src/infra/database/config_async.py`
- Modify: `src/infra/database/models/**/*.py`
- Modify: `migrations/env.py`
- Read: `plans/reports/260609-1442-async-repository-consolidation-brainstorm.md`

## Implementation Steps

1. Generate inventory files or reports from `rg` for sync imports, repository commits, and sync wrappers.
2. Add architecture tests that ban runtime imports of sync `get_db`, `SessionLocal`, `ScopedSession`, and sync `UnitOfWork` outside an allowlist.
3. Add architecture tests that flag internal repository `commit()` calls except explicit allowlist during transition.
4. Create neutral `Base` module and update config modules to import it.
5. Update model imports to use the neutral `Base` module.
6. Verify Alembic env and model registry still see all tables.
7. Run model registry and import-boundary tests.

## Success Criteria

- [x] Static guard tests exist and currently document/allow known transition violations.
- [x] `Base` is no longer owned by sync runtime config.
- [x] Alembic metadata still sees all ORM models.
- [x] No route behavior changed.

## Risk Assessment

Risk: model import churn can break Alembic autogenerate.

Mitigation: run metadata registry tests and `alembic heads` immediately after the Base split.

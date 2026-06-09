---
phase: 1
title: "Foundation and migration safety"
status: completed
priority: P1
effort: "2-3 days"
dependencies: []
---

# Phase 1: Foundation and migration safety

## Context Links

- Report: `plans/reports/260609-0955-database-model-architecture-review.md`
- Standards: `docs/standards/db-api.md`
- DB guide: `docs/database-guide.md`

## Overview

Make database truth explicit before changing data. Fix stale docs, Alembic model discovery, metadata coverage, and migration graph checks so later migrations start from a reliable base.

## Key Insights

- `src/infra/database/models/__init__.py` omits `MealImageCacheModel` and `PendingMealImageResolutionModel`.
- `migrations/env.py` reads `Base.metadata` without importing the full model registry first.
- Runtime/migrations are PostgreSQL/Neon, while several docs still say MySQL.

## Requirements

- Functional: Alembic autogenerate and tests see every ORM table.
- Functional: docs agree PostgreSQL/Neon is canonical.
- Non-functional: no production schema change except safe migration/test guardrails.

## Architecture

Central model registry imports all ORM models. Alembic imports that registry before assigning `target_metadata`. Production schema remains Alembic-owned.

## Related Code Files

| Action | File |
|---|---|
| Modify | `src/infra/database/models/__init__.py` |
| Modify | `migrations/env.py` |
| Modify | `README.md` |
| Modify | `docs/architecture/infrastructure.md` |
| Modify | `docs/architecture/core.md` |
| Modify | `docs/external-services.md` |
| Modify | `docs/project-overview-pdr.md` |
| Modify/Add | `tests/migrations/test_alembic_revision_graph.py` |
| Create | `tests/unit/infra/database/test_model_registry_metadata.py` |

## Implementation Steps

1. Update stale MySQL references in active docs to PostgreSQL/Neon. Mark old specs as historical where needed.
2. Import `MealImageCacheModel` and `PendingMealImageResolutionModel` in the central model registry and `__all__`.
3. Import `src.infra.database.models` in `migrations/env.py` before `target_metadata = Base.metadata`.
4. Add a metadata test asserting expected table names exist in `Base.metadata.tables`.
5. Extend migration graph test to assert one head and current head format.
6. Run `alembic heads`, `pytest tests/migrations/test_alembic_revision_graph.py tests/unit/infra/database/test_model_registry_metadata.py`.

## Test Scenario Matrix

| Scenario | Test |
|---|---|
| Registry includes pgvector/cache tables | metadata table assertion |
| Alembic has one head | migration graph test |
| Autogenerate sees registry | lightweight import/metadata test |
| Docs no longer state active MySQL runtime | `rg "MySQL|mysql" README.md docs` review |

## Success Criteria

- [x] `Base.metadata.tables` includes all current ORM tables.
- [x] `alembic heads` returns exactly one head.
- [x] Docs no longer conflict on canonical DB engine.
- [x] No app behavior changes.

## Risk Assessment

Low runtime risk. Main risk is import side effects in Alembic. Keep registry imports model-only; do not import repositories or runtime services.

## Security Considerations

No sensitive data access. Do not read `.env` or log DB URLs.

## Next Steps

After this phase, generate the first normalized migration from a complete metadata view.

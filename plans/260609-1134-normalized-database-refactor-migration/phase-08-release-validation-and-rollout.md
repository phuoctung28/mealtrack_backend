---
phase: 8
title: "Release validation and rollout"
status: completed
priority: P1
effort: "3-5 days"
dependencies: [1, 2, 3, 4, 5, 6, 7]
---

# Phase 8: Release validation and rollout

## Context Links

- Testing standards: `docs/testing-standards.md`
- Migration commands: `docs/database-guide.md`
- Standards: `docs/standards/db-api.md`

## Overview

Verify migrations, fallback behavior, rollback paths, and documentation before deploy. This phase is the release gate for production data safety.

## Key Insights

- The risky part is not creating tables; it is old data, old API contracts, and partial deploy rollback.
- Do not declare complete until migrations run from empty DB and current DB head.

## Requirements

- Functional: all critical flows pass after upgrade.
- Functional: backward compatibility is tested for legacy rows.
- Non-functional: deploy has a rollback/forward-fix path and preflight query checklist.

## Architecture

Use migration preflight + staged deployment:

1. Run preflight orphan/malformed JSON checks.
2. Deploy expand migrations.
3. Deploy dual-write code.
4. Verify dual writes in production.
5. Flip reads.
6. Contract legacy columns in later release only.

## Related Code Files

| Action | File |
|---|---|
| Modify | `docs/database-guide.md` |
| Modify | `docs/project-changelog.md` if present |
| Modify | `docs/development-roadmap.md` if present |
| Modify | `docs/standards/db-api.md` if plan reveals new rules |
| Modify/Add | migration tests under `tests/migrations/` |
| Modify/Add | integration tests under `tests/integration/` |

## Implementation Steps

1. Build a release checklist covering preflight SQL, backup, migration command, smoke tests, rollback/forward-fix notes.
2. Run from current head:
   - `alembic heads`
   - `alembic upgrade head`
   - targeted migration tests
3. Run from empty/test DB path if available to verify first-deploy schema creation/migrations.
4. Run targeted test suites:
   - `pytest tests/migrations/`
   - `pytest tests/integration/test_delete_account_api.py`
   - profile/hydration/saved suggestion/food/notification/referral targeted tests
5. Run quality gates:
   - `black src/ tests/`
   - `ruff check src/`
   - `mypy src/`
6. Update docs/changelog with final table inventory and legacy compatibility status.
7. Remove or production-disable first-deployment `Base.metadata.create_all()` fallback; keep `create_all()` only in tests/local tooling if still useful.
8. Prepare contract-phase follow-up list for legacy JSON columns that remain.

## Test Scenario Matrix

| Scenario | Test |
|---|---|
| Current DB upgrades to latest head | Alembic upgrade |
| Empty DB migrates to latest head | migration smoke |
| Legacy rows still read | fallback tests |
| New writes dual-write | repository integration |
| Account deletion honors ownership | integration test |
| API response shapes unchanged | route tests |
| Production startup does not create schema outside Alembic | migration/startup smoke test |

## Success Criteria

- [x] Single Alembic head.
- [x] Upgrade path verified.
- [x] Legacy + normalized compatibility tests pass.
- [x] Docs list new normalized tables and remaining temporary JSON fields.
- [x] Rollback/forward-fix plan exists for each deployed migration.
- [x] Production first-deploy path is Alembic-only.

## Risk Assessment

High release risk because real user data is involved. Mitigation: preflight SQL, backup, idempotent migrations, phased deploy, and no same-release drops of legacy columns.

## Security Considerations

Avoid dumping PII or health/payment JSON in logs while diagnosing migration failures. Preflight reports should count and classify rows, not print raw payloads.

## Next Steps

After this phase and production observation, create a separate contract plan to remove legacy JSON/columns safely.

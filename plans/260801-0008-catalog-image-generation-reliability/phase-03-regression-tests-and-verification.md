---
phase: 3
title: "Regression Tests and Verification"
status: completed
priority: P1
effort: "1.5h"
dependencies: [1, 2]
---

# Phase 3: Regression Tests and Verification

## Overview

Characterize the broken paths, run targeted validation, and verify no catalog/admin/direct-upload behavior regresses.

## Related Code Files

- Modify: `tests/unit/scripts/test_generate_catalog_meal_images.py`.
- Read: `tests/unit/infra/test_cloudinary_image_store.py`, `tests/unit/api/test_admin_meal_catalog_route.py`, and direct-upload signature tests.

## Implementation Steps

1. Add async tests that prove the generator runs after the read UoW exits and persistence opens a separate UoW only after a successful URL.
2. Cover provider failure, conditional-update skip, successful update, and persistence failure cleanup/counts.
3. Run script, Cloudinary adapter, Cloudflare generator, admin endpoint, and direct-upload signature tests.
4. Run compile, targeted Ruff, mypy on touched modules when feasible, and `git diff --check`.
5. Reviewer verifies error handling, log privacy, transaction boundaries, public-contract stability, and operational remediation.

## Success Criteria

- [x] Targeted tests pass with no live external calls.
- [x] Python compilation and touched-file quality checks pass.
- [x] Review finds no security or contract regression.

## Risk Assessment

- Unit tests must not encode `AsyncUnitOfWork` internals so tightly that normal refactors break them. Assert observable ordering and summaries with fakes instead.

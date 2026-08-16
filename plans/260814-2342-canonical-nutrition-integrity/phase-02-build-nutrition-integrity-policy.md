---
phase: 2
title: "Build Nutrition Integrity Policy"
status: completed
effort: 2d
---

# Phase 2: Build Nutrition Integrity Policy

## Context Links

- [Approved architecture](../reports/brainstorm-260814-2342-canonical-nutrition-integrity.md)
- `src/domain/services/nutrition_resolver.py`
- `src/infra/adapters/fat_secret_service.py`
- `src/infra/repositories/food_reference_projection.py`
- `src/app/services/food_reference_validation_service.py`
- `src/app/services/catalog_food_reference_review_service.py`
- `src/app/handlers/query_handlers/lookup_barcode_query_handler.py`
- every repository/import path found by searching writes of `is_verified`

## Overview

Priority P1. Extract one backend policy used by parse, search, provider resolution, catalog approval, and manual save. It validates structural and catastrophic correctness without claiming every plausible external identity is true.

## Key Insights

- `is_verified=true` does not enforce nutrition integrity; production has verified catastrophic rows.
- Canonical `g` means one gram, while the provider mapping currently overloads `g` with a 100g serving.
- Best-effort validation that never blocks is insufficient at trust boundaries.

## Requirements And Architecture

- Freeze `nutrition_integrity_v1`: structured references require finite P/C/F, each in `[0,100]` g/100g; `P+C+F <= 110`; finite fiber/sugar each in `[0,100]` with no `fiber <= carbs` or `fiber+sugar <= carbs` rule; backend-derived energy in `[0,900]` kcal/100g; advertised energy, when required, must be finite in `[0,900]` and differ from derived energy by no more than `max(20 kcal, 20%)` inclusive.
- V1 serving rules: normalized basis is 100g; every conversion is finite and positive within the existing 10kg item bound; canonical base `g` is exactly 1 gram. Identity/preparation acceptance remains a separate resolver rule rather than a numeric quarantine rule.
- Exactly one normalized logical source origin and stable low-cardinality reason codes.
- Normalize provider `100 g` as a labelled 100g serving, never as base-unit `g=100`.
- Application/infra adapters call the policy; the domain policy imports no I/O.
- Maintain an enforcement matrix: parse finalization, search output, catalog approval/trusted upsert, create, and edit fail closed; best-effort scans may report without mutating but cannot satisfy an enforcement gate.

## Related Code Files

Modify:

- `src/domain/services/nutrition_resolver.py`
- `src/domain/services/food_mapping_service.py`
- `src/infra/adapters/fat_secret_service.py`
- `src/infra/repositories/food_reference_projection.py`
- `src/app/services/food_reference_validation_service.py`
- `src/api/dependencies/event_bus.py`
- corresponding existing resolver, adapter, mapping, and validation tests

Create:

- `src/domain/services/nutrition_integrity_policy.py`
- `tests/unit/domain/services/test_nutrition_integrity_policy.py`

## TDD Implementation Steps

1. Add one versioned boundary fixture matrix for NaN/infinity, missing macros, inclusive 0/100/110/900 boundaries, just-over boundaries, energy tolerance, fiber greater than carbs, fiber+sugar greater than carbs, conflicting origins, bad servings, and `g != 1`.
2. Add production-shaped fixtures, including verified catastrophic rows, without copying PII.
3. Implement a pure policy result with accepted/rejected status and reason code.
4. Move reusable checks from parse orchestration into the policy and keep parse behavior green.
5. Normalize FatSecret serving mapping and canonical projection through one serving invariant.
6. Wire dependency construction and each enforcing call site to the shared policy; inventory every `is_verified` write and require the policy before approval/trusted upsert. Keep `FoodReferenceValidationService` advisory only while it catches failures and returns unchanged data.
7. Publish the fixture matrix as the canonical cross-layer contract, run it through the domain policy and enforcement-matrix tests, and prove each trust boundary rejects a policy failure. Phase 6 must reuse the same fixtures for the audit classifier and SQL constraints; advisory scan failures cannot be mistaken for acceptance.

## Verification

- Targeted policy, resolver, mapping, adapter, and validation unit tests.
- `python scripts/development/evaluate_parse_text_nutrition.py --mode offline`
- `ruff format --check src/domain/services/nutrition_integrity_policy.py src/domain/services/nutrition_resolver.py src/infra/adapters/fat_secret_service.py`
- `ruff check src/domain/services/nutrition_integrity_policy.py src/domain/services/nutrition_resolver.py src/infra/adapters/fat_secret_service.py`
- `mypy src/domain/services/nutrition_integrity_policy.py src/domain/services/nutrition_resolver.py`
- `lint-imports`.

## Verification Evidence

- Selected base verified after `git fetch origin delivery`: `origin/delivery` resolves to `5415897c55173f446229441afbc0a79ed80c3f2f`.
- Targeted nutrition, resolver, adapter, repository, validation, parse, recommendation, and contract suite: 162 passed, 1 deselected.
- Offline parse-text evaluator: 10 synthetic cases passed; this does not claim live-provider or deployment evidence.
- Ruff check/format, virtualenv mypy, compileall, `git diff --check`, and `lint-imports` passed.
- Full unit command reached 2,314 passed with one unrelated failure in the pre-existing cron/onboarding WIP: `tests/unit/cron/test_push_cron.py::test_push_cron_phase_failure_does_not_abort_subsequent_phases` expects one exception capture while the new local claim-promotion path raises a missing `onboarding_completed_at` column error.

## Success Criteria

- [x] One policy governs all structured nutrition trust boundaries.
- [x] The Python policy owns one canonical V1 fixture matrix; Phase 6 is explicitly gated on applying those exact fixtures to its audit classifier and SQL constraints.
- [x] Base `g` always maps to one gram; 100g remains a separate serving.
- [x] Production-shaped catastrophic fixtures fail closed with stable reason codes.
- [x] Every editorial verification write path invokes the same integrity gate.
- [x] Parse-text corpus remains green.

## Risks, Security, And Rollout Gate

- Risk: duplicated rules drift. Mitigation: remove orchestration-local validation after equivalence tests.
- Risk: over-strict plausible-data rejection. Mitigation: V1 preserves the existing 110g macro-mass tolerance and nonnegative independent fiber/sugar semantics; changing thresholds requires a new policy version, reviewed reclassification, and cache generation.
- Security: metrics expose operation/source/reason only.
- Gate: shared-policy suites and Phase 1 contracts green.

## Unresolved Questions

None.

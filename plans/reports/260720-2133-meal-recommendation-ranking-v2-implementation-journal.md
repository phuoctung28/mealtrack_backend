# Meal Recommendation Ranking V2

**Date**: 2026-07-20 21:33
**Severity**: Medium
**Component**: meal recommendation ranking / rollout
**Status**: Resolved

## What Happened

Implemented default-off `catalog_deterministic_v2` with snapshot-scoped IDF, confidence-scaled ingredient similarity, bounded top-30 diversity reranking, versioned rollout modes (`v1`, `shadow`, `cohort`, `v2`), deterministic cohorting, and privacy-safe shadow metrics. `v1` stays the default and replay-safe. No migration, mobile, or API schema change was required.

## The Brutal Truth

The ranking logic is done. The rollout proof is not. Local verification is strong, but shipping this without staging p95 and representative quality evidence would be blind optimism dressed up as confidence. That is exactly how teams end up re-litigating "done" after the fact.

## Technical Details

- Deterministic cohorting with versioned rollout modes: `v1`, `shadow`, `cohort`, `v2`
- Snapshot-scoped IDF
- Confidence-scaled cosine ingredient similarity
- Bounded top-30 diversity reranking
- Privacy-safe shadow metrics
- Verification: focused ranking suite `97 passed`; full unit suite `1993 passed, 14 warnings`
- Tooling checks: `lint-imports` kept `4 contracts`; scoped Ruff clean; `compileall` clean; `git diff --check` clean
- Benchmark artifact: [`plans/reports/meal-recommendation-ranking-v2-final.json`](./meal-recommendation-ranking-v2-final.json)
- Synthetic v2 p95: `9.7713 ms` / `17.417 ms` / `67.1577 ms` for catalog sizes `180` / `1000` / `5000`

## What We Tried

- Kept the contract additive instead of touching stored-plan schema or client code
- Validated the ranking path locally before exposure
- Used privacy-safe shadow metrics so rollout can observe behavior without leaking sensitive inputs

## Root Cause Analysis

The hard part was not the scoring math. It was preserving deterministic replay while adding a new ranking path that can be rolled out, shadowed, and rolled back without mutating persisted plans. The obvious alternative, coupling v2 to schema or mobile changes, would have made rollback slower and riskier.

## Lessons Learned

A ranking upgrade is only real once the rollout path is versioned, deterministic, and reversible. Local correctness is necessary, not sufficient, and synthetic benchmarks are still not a substitute for representative staging evidence.

## Next Steps

- Run staging p95 against representative catalogs
- Collect quality evidence on real recommendation outputs
- Promote only if v2 stays bounded and replay-safe under production-like load

**Status:** DONE
**Summary:** Local v2 implementation is complete and verified; `v1` remains default, rollout is reversible, and benchmark/test gates passed.
**Concerns:** Staging p95 and representative quality evidence are still missing, so production promotion is not ready yet.

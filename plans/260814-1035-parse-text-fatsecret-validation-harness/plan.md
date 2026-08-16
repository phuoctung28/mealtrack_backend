---
title: "Parse-Text FatSecret Validation Harness"
description: "TDD hardening for parse-text identity extraction, structured nutrition resolution, and semantic evaluation gates."
status: completed
priority: P1
branch: "delivery"
tags: [bugfix, backend, api, critical, ai, nutrition, tdd]
blockedBy: []
blocks: []
created: "2026-08-14"
createdBy: "ck:plan"
source: skill
---

# Parse-Text FatSecret Validation Harness

## Overview

Prevent semantically absurd parse-text nutrition such as `100gr khoai tay`
returning about 890 kcal. Keep both authenticated and guest response contracts
unchanged while making local/FatSecret structured nutrition authoritative after
a confident identity match. AI macros remain a bounded fallback; backend macro
calculation remains the only calorie source. Full vector RAG is out of scope.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Characterize Parse-Text Nutrition Contracts](./phase-01-characterize-parse-text-nutrition-contracts.md) | Completed |
| 2 | [Implement Structured Reference Resolution](./phase-02-implement-structured-reference-resolution.md) | Completed |
| 3 | [Build Evaluation Harness And Release Gates](./phase-03-build-evaluation-harness-and-release-gates.md) | Completed |

## Dependencies

- Sequential execution: Phase 1 -> Phase 2 -> Phase 3.
- No blocking plan was found. The preparation-aware catalog plan is related but
  does not own this handler, contract, or harness.
- Reuse the existing staged FatSecret APIs and nutrition resolver seams; do not
  add a new retrieval subsystem.

## Research

- [Approved design](../reports/260814-1023-parse-text-fatsecret-validation-harness.md)
- [Code-path and TDD research](../reports/260814-1030-parse-text-codepath-tdd-research.md)
- [Harness and retrieval research](../reports/260814-1030-parse-text-harness-retrieval-research.md)

## Release Boundary

- No DB migration, mobile change, image-scan change, provider migration, or RAG.
- No rollout until offline goldens pass and an explicit staging run reports
  accuracy, fallback rate, provider-call count, and p50/p95 latency.
- Preserve unrelated worktree edits, especially current changes in
  `docs/external-services.md`.

## Validation

- Standard tier: Fact Checker + Contract Verifier, 10 claims per phase.
- Public DTO/route compatibility and controlled 422 failure behavior are gates.

## Red Team Review

- 2026-08-14: 26 findings; 25 accepted, 1 rejected as unrelated pre-existing
  guest-identity scope. Breakdown: 2 Critical, 18 High, 6 Medium.
- [Adjudication and applied changes](../reports/260814-1055-red-team-adjudication-parse-text-plan.md)
- Consistency sweep: 4 plan files reread, 11 deltas reconciled, 0 unresolved.

## Validation Log

- 2026-08-14 auto validation; questions asked: 0 because the approved design and
  red-team adjudication leave no unresolved product choice.
- Standard tier: 30 claims checked, 30 verified, 0 failed, 0 unverified.
- [Fact Checker and Contract Verifier results](../reports/260814-1105-parse-text-plan-validation.md)
- Final consistency sweep: 4 plan files, 0 stale decisions, 0 contradictions.
- Implementation verification: focused `.venv/bin/pytest` slices for the handler, routes, resolver, calorie parity, FatSecret adapter, eval loop, and evaluation CLI passed (120 tests).
- Offline 10-case gates now pass after the optional local-reference energy handling fix in the current tree.
- The separate architecture suite still has three unrelated dirty-tree failures
  (transaction allowlists and the existing domain-service count threshold); these
  are recorded in the PM report and are not attributed to this sync.

## Unresolved Questions

None. Candidate and energy tolerances are implementation constants calibrated
by fixtures; lowering quality gates requires a new product decision.

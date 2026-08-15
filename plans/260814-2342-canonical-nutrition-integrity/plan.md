---
title: "Canonical Nutrition Integrity"
description: "Deep TDD cutover to backend-authoritative nutrition identity, persistence, Flutter preview, and reversible production quarantine."
status: in-progress
priority: P1
branch: "feature/canonical-nutrition-integrity-phase-04"
effort: 16d
tags: [backend, mobile, api, nutrition, tdd, critical]
blockedBy: []
blocks: [260729-1930-preparation-aware-catalog-resolution]
created: "2026-08-14T16:56:27.979Z"
createdBy: "ck:plan"
source: skill
---

# Canonical Nutrition Integrity

## Overview

Fix the failure class behind the 890-kcal potato incident by making source identity and normalized nutrition survive search/parse, preview, save, persistence, and edit. Backend remains the sole calorie authority. Flutter may scale backend calories and macros by portion but never derive calories from macros.

The rollout is additive and backend-first: deploy parse-text containment, freeze contracts, centralize integrity policy, resolve references on save, implement Flutter compatibility, quarantine invalid production rows, then release Flutter. This prevents catastrophic or tampered data; plausible but semantically incorrect provider records still require provenance, preparation-aware matching, and review.

## Ownership Contract

| Concern | Owner |
|---|---|
| Source resolution, integrity validation, calorie derivation, persisted totals | Backend |
| Portion input and temporary proportional preview | Flutter |
| Canonical catalog verification and quarantine | Backend operations/reviewer |

Every item resolves to exactly one logical origin: `food_reference_id`, `fdc_id`, namespaced provider `food_id`, or explicit custom. Versioned clients send a per-item discriminator plus `nutrition_contract_version=2`. Multiple reference IDs are rejected. Only payloads with both version and discriminator absent enter the legacy path. `nutrition_override` remains a separate explicit user-entered exception; mobile never synthesizes one from macros/provider data, and backend validates/audits it independently from immutable source nutrition.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Lock Contracts and Contain Production](./phase-01-lock-contracts-and-contain-production.md) | Completed |
| 2 | [Build Nutrition Integrity Policy](./phase-02-build-nutrition-integrity-policy.md) | Completed |
| 3 | [Normalize Search and Source Resolution](./phase-03-normalize-search-and-source-resolution.md) | Completed |
| 4 | [Make Create And Edit Reference Authoritative](./phase-04-make-manual-save-reference-authoritative.md) | Completed |
| 5 | [Cut Over Flutter Nutrition Authority](./phase-05-cut-over-flutter-nutrition-authority.md) | Pending |
| 6 | [Quarantine Data and Release Safely](./phase-06-quarantine-data-and-release-safely.md) | Pending |

## Dependencies

- Completed prerequisite: [parse-text FatSecret validation harness](../260814-1035-parse-text-fatsecret-validation-harness/plan.md) merged and deployed to SIT from `delivery` SHA `5415897c55173f446229441afbc0a79ed80c3f2f`.
- Blocks [preparation-aware catalog ingredient resolution](../260729-1930-preparation-aware-catalog-resolution/plan.md) until shared integrity and provenance gates land.
- Backend additive API must be live before the Flutter cutover.
- The user chose not to use additional worktrees. Every backend implementation session must fetch latest `origin/delivery`, verify its selected base SHA, preserve unrelated WIP, and stage only phase-owned files. Flutter must likewise start from freshly fetched remote `main`, never stale local `main`.
- Production quarantine requires read-only audit, reviewed versioned manifest, dry-run diff, row lock/compare-and-swap guard, and separate operations approval.

## Evidence

- [Phase 1 completion report](../reports/pm-260815-1356-canonical-nutrition-phase-01-complete.md)
- [Debugger report](../reports/debugger-260814-2342-canonical-nutrition-integrity.md)
- [Approved architecture](../reports/brainstorm-260814-2342-canonical-nutrition-integrity.md)
- [Backend contract research](./research/backend-contract-and-persistence.md)
- [Flutter contract research](./research/flutter-contract-and-preview.md)
- [Production data and rollout research](./research/data-quality-rollout.md)

## Definition Of Done

- Invalid structured nutrition and invalid gram semantics fail closed before search/save/verification.
- Local structured saves persist canonical identity and ignore client nutrition.
- Flutter preserves identity and scales backend calorie density without a formula.
- Save response replaces preview/cache; create and edit use the same authority contract.
- Create/edit retries are user-scoped and idempotent; unauthorized or rate-rejected operations perform no provider work.
- Invalid verified production rows are reversibly quarantined and constraints validate afterward.
- Old-client compatibility is measured and removed only after an explicit sunset gate.
- Staging, provider-outage, old-client, Vietnamese search, migration, and physical-device flows pass.
- `lint-imports` remains green after new ports and dependency wiring.

## Red Team Review

[Completed](./reports/red-team-review.md): seven independent reviews produced 32 accepted trust, persistence, concurrency, migration, compatibility, scope, and rollout amendments. No approved ownership decision was reversed.

## Validation Log

Validated after seven independent code-backed reviews: all 32 accepted findings are represented and both final reviewers report zero remaining blockers. Phase 1 closed on 2026-08-15 after PR #509 merged at `5415897c55173f446229441afbc0a79ed80c3f2f`, its SIT image built successfully, and the live potato sentinel returned 85.3 kcal. Phase 2 closed after the shared integrity policy, canonical serving normalization, fail-closed trust-boundary gates, and focused suites passed; the broad unit gate retains one unrelated cron/onboarding WIP failure documented in the Phase 2 verification evidence. Phase 3 closed on 2026-08-15 on `feature/canonical-nutrition-integrity-phase-03`: focused identity/search/parse/repository suites passed, offline evaluation passed 10 synthetic cases, and 2332 unit tests passed with the unrelated cron WIP test excluded. Phase 3 closeout also made local search batch fetching exhaustive until the valid limit is filled, made provider identity absence degrade instead of claim provider authority, versioned search cache keys with `nutrition_integrity_v1`, and added verified-only filtering, serving normalization, and source-identity preservation after review. Phase 4 closed on 2026-08-15 on `feature/canonical-nutrition-integrity-phase-04`: v2 manual create/edit now resolve through one backend authority, use authoritative snapshot serving weights during aggregation, persist immutable source snapshots, reserve idempotency in a short transaction before external resolution, clean old terminal records in bounded batches, and return snapshot-backed authoritative detail. The focused Phase 4 regression suite passed 109 tests and the filtered unit gate passed 2360 tests at 78.83% coverage. Migration application remains an environment gate because this checkout has no valid `DATABASE_URL`; the migration was not applied locally. Broader integration attempts remain environment-blocked by existing schema and fixture setup drift.

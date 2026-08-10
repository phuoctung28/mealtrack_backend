---
title: "OpenAI Translation Service Cutover"
description: "Replace DeepL runtime translation with neutral OpenAI-backed translation contracts, callers, and release gates."
status: in-progress
priority: P2
effort: 5d
branch: "phuoctung28/bramble"
tags: [backend, api, refactor]
mode: deep-tdd
blockedBy: []
blocks: []
created: "2026-08-09"
createdBy: "ck:plan"
source: skill
---

# OpenAI Translation Service Cutover

## Overview

Deep-TDD cutover: keep runtime additive through Phases 1-4; delete DeepL last.
Scope covers neutral contract, OpenAI adapter, all callers, persistence, and release verification; excludes DB migration/backfill, public endpoint, model upgrade, and fallback.
Inputs: [Brainstorm](../reports/260809-1149-openai-translation-service-brainstorm.md), [Deep Scout](./reports/deep-scout-report.md).

Locked policies:
- Same-language passthrough; unsupported pair returns `UNAVAILABLE`.
- Translation invocations force `store=False`; no raw text, prompt, translated payload, or provider error-body logging.
- Only `TRANSLATED` may enter non-English locale caches or persisted translation rows; canonical English persistence remains allowed in its canonical stores.
- Barcode storage stays canonical English; target-locale barcode text is response projection only.
- Partial results may render canonical-filled mixed presentation, but never locale-cache/persist as localized artifacts.
- No DB migration, no backfill, no new cache family, and no suggestion-save redesign; preserve migrations, archives, planning journals, and completed-plan history.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Neutral Translation Contract](./phase-01-neutral-translation-contract.md) | Completed |
| 2 | [OpenAI Structured Translation Adapter](./phase-02-openai-structured-translation-adapter.md) | Completed |
| 3 | [Read Path and Presentation Cutover](./phase-03-read-path-and-presentation-cutover.md) | Completed |
| 4 | [Persisted Meal and Suggestion Cutover](./phase-04-persisted-meal-and-suggestion-cutover.md) | Completed |
| 5 | [DeepL Removal and Release Verification](./phase-05-deepl-removal-and-release-verification.md) | In Progress |

## Red Team Review

Session: 2026-08-09. Raw findings: 27. Deduped findings: 15. Severity: 6 Critical / 8 High / 1 Medium.
User approval: Option 1 approved on Sunday, August 9, 2026. Apply all 14 accepted findings; keep rejection of finding 15.

| Disposition | Findings | Applied To |
|---|---|---|
| Accept / Accept-modified | F01-F14 | Phases 1-5 per adjudication report |
| Reject | F15 | No suggestion-save redesign |

### Whole-Plan Consistency Sweep

- Files reread: `plan.md` and all five phase files.
- Decision deltas checked: 14; stale references reconciled: 14.
- Unresolved contradictions: 0.

## Validation Log

### Session 1 — 2026-08-09 (evidence-backed red-team corrections; 1 question)

1. **[Risk/Scope]** How should the 15 deduplicated findings be handled before plan edits?
   - Options: Apply 14 accepted findings (recommended) | Review each | Reject all. **Answer:** Apply 14; retain rejected save-redesign boundary.

**Verification:** Full tier; reviewers sampled 225 claims (169 verified, 45 failed, 11 unverified before correction). No unresolved verification tags remain after propagation.
**Confirmed:** forced translation `store=False`; distinct Phase-3 getter; canonical English barcode storage; bounded translation; translated-only non-English cache/persistence; no DB migration/backfill/public endpoint/save redesign.
**Impact:** Findings propagated across Phases 1-5; consistency sweep found no unresolved contradiction.

### Session 2 — 2026-08-09 (implementation validation; 1 pre-existing gate failure)

- `uv run --python 3.13.2 lint-imports`: passed.
- `uv run --python 3.13.2 pytest tests/unit --cov=src --cov-fail-under=65`: passed, 2231 passed / 0 failed / 44 warnings, 79.33% coverage.
- `uv run --python 3.13.2 pytest tests/integration/ai/test_openai_translation_smoke.py`: skipped cleanly in this environment.
- `tests/architecture/test_async_db_runtime_boundaries.py::test_repository_transaction_boundary_allowlist_does_not_expand`: failed on the pre-existing allowlist mismatch in `src/infra/repositories/admin_meal_catalog_repository_async.py`.
- Impact: translation cutover implementation is complete, but the release gate stays open until the pre-existing allowlist mismatch and repository-wide Ruff/format baseline are reconciled or explicitly re-approved.

## Dependencies

- `blockedBy: []`, `blocks: []`; coordination-only overlap with `260720-2133-meal-recommendation-ranking-v2`, `260727-1905-slot-only-recommendation-replenishment`, and `260612-1046-service-initiated-bandwidth-reduction`.
- Do not parallelize Phases 3-5; they share DI, recommendation, scan, and translation-persistence surfaces.

## Success Gates

- Phase order stays additive: no runtime deletion before Phase 5.
- Layer gate is `lint-imports` plus `uv run --python 3.13.2 pytest tests/architecture/test_layer_boundaries.py::TestDomainLayerBoundaries -q`.
- Release gate adds no-upgrade lock diff review, zero active DeepL residue including `.importlinter`, and a credential-gated smoke boundary.
- Current state: release gate remains open because the async repository allowlist still fails on the pre-existing `admin_meal_catalog_repository_async.py` mismatch and the repository-wide Ruff/format baseline is not green.

# Docs Impact Report: LLM Nutrition Output Contracts Phase 3

**Date:** 2026-06-13
**Scope:** docs only
**Decision:** Docs impact is minor, but updating the top-level docs was warranted because Phase 3 changed the user-facing AI failure contract.

## Current State Assessment

- Phase 2 docs already covered canonical AI nutrition contracts and backend-derived calories.
- Phase 3 adds a stricter runtime behavior: invalid structured AI output retries exactly once for meal image scan and text parse, then fails through controlled `AIOutputValidationError`.
- Ingredient recognition keeps the unstructured `{name, confidence, category}` contract.
- FatSecret divergence checks in text parsing now compare against backend-derived macro calories.

## Changes Made

- Updated [`docs/project-overview-pdr.md`](../../docs/project-overview-pdr.md) to record the validation-retry behavior in the overview, status line, and version history.
- Updated [`docs/project-roadmap.md`](../../docs/project-roadmap.md) to mark the Vision Parser Resilience phase as including the one-retry validation contract.
- Updated [`docs/codebase-summary.md`](../../docs/codebase-summary.md) to summarize the new validation retry behavior alongside the existing canonical nutrition contracts.
- Regenerated `repomix-output.xml` as required by workspace documentation workflow.

## Gaps Identified

- Existing docs validation still reports unrelated stale references in:
  - `docs/database-guide.md`
  - `docs/hydration-api-gaps.md`
  - `docs/movement-release-readiness.md`
  - `docs/troubleshooting.md`
  - `docs/external-services.md`
- Those warnings are pre-existing and not caused by this phase.

## Recommendations

1. Keep the current docs delta as-is.
2. Handle the validator warnings in a separate cleanup pass so this phase stays narrowly documented.
3. If Phase 4 changes parser flow again, update the same three top-level docs rather than creating a new ad hoc note.

## Metrics

- Docs files updated: 3
- Source files touched: 0
- Test files touched: 0
- Doc validator: passed with unrelated pre-existing warnings
- Overall docs impact: minor

## Unresolved Questions

- None.

# OpenAI Translation Cutover Docs Sync

**Date:** 2026-08-09  
**Scope:** Documentation only  
**Docs impact:** minor

## Current State Assessment

The translation cutover is implemented in code and the docs were partially stale around ownership, privacy, and rollback behavior.

## Changes Made

- Updated `docs/external-services.md` with OpenAI translation ownership, `store_responses=False`, and the translation outcome gate for persistence/cache admission.
- Updated `docs/system-architecture.md` with the read-path translation boundary and the `TranslationOutcome.TRANSLATED` gate.
- Updated `docs/runbooks/provider-outage.md` with a stricter translation-provider rollback procedure and the affected cache-window handling.
- Refreshed `docs/codebase-summary.md` to point at the new read-path localization owner and the OpenAI translation adapter.
- Regenerated `repomix-output.xml` for the current repo snapshot.

## Gaps Identified

- `docs/runbooks/provider-outage.md` still uses a generic `food-search` cache namespace description; it is accurate enough for rollback, but not provider-specific provenance.
- Docs validation reported unrelated legacy drift in other files, mostly pre-existing code-reference and config-key warnings outside this scope.

## Recommendations

1. Keep the translation rollback note aligned with any future cache-namespace naming changes.
2. Review the unrelated docs-validation warnings in a separate sweep.
3. Preserve the current privacy rule: no payload storage, no raw translation payload logging, and no persistence for non-`TRANSLATED` outcomes.

## Verification

- Ran `node $HOME/.claude/scripts/validate-docs.cjs docs/`
- Validation completed successfully with unrelated pre-existing warnings only.


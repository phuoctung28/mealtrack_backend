# OpenAI Translation Service Cutover

**Date**: 2026-08-09 16:10
**Severity**: Medium
**Component**: Translation architecture, persistence, and release gates
**Status**: Blocked

## What Happened

We finished the OpenAI translation service cutover and removed the DeepL runtime path from the active implementation. The work was not a simple provider swap. It replaced the vendor-shaped translation flow with a neutral contract, a dedicated OpenAI adapter, and separate read/write call sites so presentation translation, cache admission, and persistence no longer share the same assumptions.

The cutover also locked the privacy boundary: translation requests force `store=False`, and we kept raw source text, translated payloads, and provider error bodies out of logs. On the data side, only `TRANSLATED` results are allowed into non-English locale caches or persisted translation rows. Canonical English storage stays in its canonical path, and partial results may still render as mixed presentation without being treated as durable localized data.

## The Brutal Truth

This was the kind of cutover that punishes sloppy thinking. If we had treated translation as “just another AI call,” we would have quietly poisoned caches, persisted fallback text, and made rollback meaningless. The annoying part is that the hard work was mostly boundary work: proving what may be cached, what may be stored, and what must stay canonical. That is tedious, but it is the difference between a controlled migration and a slow-motion data integrity problem.

## Technical Details

- Scope moved across 59 files in the live diff: new neutral translation types/services, OpenAI adapter wiring, read-path and persistence callers, and removal of DeepL runtime modules.
- Validation passed:
  - `uv run --python 3.13.2 lint-imports`
  - `uv run --python 3.13.2 pytest tests/unit --cov=src --cov-fail-under=65`
  - `uv run --python 3.13.2 pytest tests/integration/ai/test_openai_translation_smoke.py` skipped cleanly
- Post-fix full unit gate: `2305 passed`, `44 warnings`, `79.99%` coverage after merging `origin/delivery`.
- Focused semantic, metadata, empty, and concurrency checks passed.
- Residue gate is reconciled.
- Known failure: `tests/architecture/test_async_db_runtime_boundaries.py::test_repository_transaction_boundary_allowlist_does_not_expand` failed on the pre-existing allowlist mismatch in `src/infra/repositories/admin_meal_catalog_repository_async.py`.
- Repository-wide Ruff/format checks remain red on baseline debt; focused adapter, fixture, compile, mypy, and import-boundary checks are green.

## What We Tried

- Rebuilt the translation surface around a neutral `TextTranslationPort` instead of keeping DeepL names in the runtime path.
- Split read-path translation from persisted translation so the cache and database only admit translated outputs when the adapter actually returns a translated result.
- Kept the release gate honest by running the unit suite, targeted translation tests, and the architecture boundary check instead of pretending a green partial run was enough.

## Root Cause Analysis

The original problem was architectural drift. Provider-specific translation semantics, cache policy, and persistence policy were tangled together. That made it too easy to let fallback text look durable. The cutover fixed that by forcing the translation outcome to be explicit and by separating canonical English storage from localized presentation artifacts.

## Lessons Learned

- Translation needs an outcome model, not a provider-shaped wrapper.
- Cache admission and persistence must be gated by translation success, not by hopeful string content.
- Privacy rules are part of the design, not a logging afterthought.
- A passing unit suite does not clear a release if the architecture gate already knows the repo is drifting.

## Next Steps

- Reconcile or explicitly re-approve the `admin_meal_catalog_repository_async.py` transaction-boundary allowlist mismatch.
- Re-run the architecture gate after that decision.
- Keep the translation release blocked until the allowlist issue is resolved.

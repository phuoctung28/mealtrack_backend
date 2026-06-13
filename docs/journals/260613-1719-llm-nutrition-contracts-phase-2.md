# LLM Nutrition Contracts Phase 2

**Date**: 2026-06-13 17:19
**Severity**: High
**Component**: AI nutrition output contracts
**Status**: Resolved

## What Happened

Phase 2 landed the canonical nutrition contracts for both image and text AI output. The image contract now requires a non-empty foods list and bounded `quantity_g`, while the text contract preserves the current UX by keeping `quantity` and `unit` and normalizing current flat macro fields into nested `macros`. AI-reported calories are ignored because backend macro math remains the source of truth. The legacy `GPTResponseParser` also stopped silently dropping invalid food quantities, so bad output now fails instead of being partially saved and patched later.

## The Brutal Truth

The previous behavior was too forgiving in the worst possible way: it made broken model output look usable. That is exactly how you end up with corrupted nutrition data and no clean failure boundary. The annoying part was that review caught a runtime partial-save risk after the first pass. We had to fix that before calling the phase done, which was the right outcome even if it meant the parser had to get less “helpful.”

## Technical Details

- Canonical contracts added for image and text nutrition AI output.
- Image contract rejects empty foods and impossible `quantity_g` values.
- Text contract keeps `quantity`/`unit` for UX and normalizes flat macro fields into nested macros.
- AI calories are ignored; calories stay derived from macros in the backend.
- `GPTResponseParser` now fails invalid food quantities instead of filtering them out.
- Verification: focused suite `65 passed`, broader Phase 1+2 suite `110 passed`, and touched-slice `ruff`, `mypy`, `black --check`, and `py_compile` all passed.
- Full-repo `ruff`, `mypy`, and `black --check` remain blocked by unrelated existing hygiene issues.

## What We Tried

We first relied on parser-side cleanup, which looked safe until review showed it could still save partial data. That approach was rejected because silent repair hides defects instead of surfacing them. The fix was to make invalid AI output fail hard at the contract boundary so Phase 3 retry orchestration can own repair behavior explicitly.

## Root Cause Analysis

The root cause was over-trusting the parser to sanitize model output. That was a design mistake, not a minor bug. Once invalid quantities were being filtered before validation, the system could not distinguish “good enough” from “silently broken,” and that is how runtime partial-save risk slipped through.

## Lessons Learned

- Do not hide model defects inside parser cleanup.
- If output is invalid, fail at the contract boundary and let retry logic decide recovery.
- Preserve UX in the text contract, but do not let UX convenience weaken validation.
- Treat review findings about partial saves as real until proven otherwise.

## Next Steps

Phase 3 should own validation retry orchestration and repair behavior. The implementation team should keep the contract boundary strict and move recovery logic out of the parser so bad AI output is either retried or rejected on purpose.

**Status:** DONE
**Summary:** Canonical image/text nutrition contracts shipped, invalid AI quantities now fail fast, and the partial-save risk was fixed after review.
**Concerns:** Full-repo `ruff`, `mypy`, and `black --check` are still blocked by unrelated existing hygiene issues.

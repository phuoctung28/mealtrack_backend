# Parse-Text FatSecret Harness Plan Locked

**Date**: 2026-08-14 11:02
**Severity**: High
**Component**: `/v1/meals/parse-text` planning and validation
**Status**: Ongoing

## What Happened

We finished the planning pass for the parse-text FatSecret validation harness and locked the scope in [`plans/260814-1035-parse-text-fatsecret-validation-harness/plan.md`](../../plans/260814-1035-parse-text-fatsecret-validation-harness/plan.md). The plan is now split into three phases: contract characterization, structured reference resolution, and an evaluation harness with release gates.

The core problem stayed ugly: `100gr khoai tây` could still come back at about 890 kcal because the current path trusts bad macros too much. The approved design keeps the public response shape unchanged, but makes structured FatSecret nutrition authoritative after a confident match instead of blindly accepting the first enriched result.

## The Brutal Truth

This was not a subtle bug. We had a nutrition pipeline that could be numerically correct and still semantically nonsense. That is exactly the kind of failure that wastes hours, ships garbage, and makes every “it passed validation” claim feel fake. The irritating part is that the old shape looked tidy right up until the potato example punched through it.

## Technical Details

The approved plan keeps parse-text on the existing handler path, but adds hard constraints the current code does not have: staged FatSecret candidate search plus one selected detail fetch, request-wide budgets, bounded `current_items`, and a single whole-request semantic retry. Red-team adjudication accepted 25 findings and rejected only the unrelated guest-limiter issue; the rest forced real corrections, especially around unbounded refinement input, request fan-out, raw-data logging, and fiber/sugar propagation.

Validation confirmed the relevant facts: both authenticated and guest routes use `ParseMealTextCommand`; the handler currently permits two total schema-validation attempts and can still fall back to AI macros; `current_items` is still unconstrained; and the current prompt harness does not measure parse-text nutrition correctness. The plan path above now reflects the approved boundary: no vector RAG, no DB migration, no mobile work, no provider swap.

## What We Tried

- Re-read the approved design, all three phase files, and the validation/adjudication reports.
- Reconciled the red-team findings against the original plan instead of hand-waving them away.
- Kept the session read-only; no production code, tests, or deployment changes were made.

## Root Cause Analysis

The root cause is a bad trust boundary. We were deriving calories correctly from macros, but we were not proving the macros belonged to the food the user actually typed. The handler also treated provider ordering and fallback paths as good enough, which is how absurd nutrition escaped through a formally valid response.

## Lessons Learned

- Structured extraction is not enough unless identity, preparation, and quantity are validated against a real reference.
- A single bad candidate must not win just because it arrived first.
- Request-wide limits matter; per-item retries and unbounded refinement are how one bad input turns into a fan-out mess.
- If a pipeline can return 890 kcal for a potato, the contract is lying somewhere upstream.

## Next Steps

Start Phase 1 characterization next, with the first command:

```bash
pytest tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py -v
```

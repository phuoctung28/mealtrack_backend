# Parse-Text FatSecret Validation Harness Implementation

**Date**: 2026-08-14 11:29 +07
**Severity**: High
**Component**: `/v1/meals/parse-text`
**Status**: Implemented/locally validated

## Context

We implemented the parse-text fix as a bounded nutrition-validation path, not a broad nutrition rewrite. The handler now treats structured FatSecret `*_100g` data as the preferred source after a confident match, and the evaluation harness measures identity, quantity, candidate selection, common-reference resolution, catastrophic outliers, and latency instead of pretending schema validity equals correctness. Live evaluation stays default-off behind a staging-only gate.

## What Happened

The old path could return a mathematically valid but semantically ridiculous result, including the potato case that inflated to about 890 kcal. We fixed the trust boundary by preferring structured reference data over raw AI macros, keeping the public response shape intact, and adding a harness that fails the release if the nutrition semantics drift again.

## Reflection

The frustrating part is that the bug was never arithmetic. We had correct calorie math wrapped around bad input and then congratulated ourselves because the schema passed. That is a stupidly expensive way to learn that “valid JSON” is not the same as “credible nutrition.” The bounded fallback and default-off rollout were the only sane choices because anything looser would just turn provider ambiguity into another silent lie.

## Decisions

We chose structured FatSecret validation over prompt-only patching, rejected vector RAG, and kept the fallback bounded instead of letting the handler keep guessing forever. The rollout is default-off, gated by explicit live-eval enablement in staging, and the harness report stays private and synthetic by default. The plan validation report closed 30/30 checks, and the local validation evidence was stronger than the earlier delegated-run caveat: focused parse-text tests passed 113/113, the non-cron CI-aligned suite passed 2274/2274 at 79.38% coverage, the offline 10-case gates passed, and changed-scope `mypy`, `ruff`, `format`, and compile checks passed. That is the real evidence that the contract changes and gates are coherent.

## Next Steps

1. Keep the live-eval flag off until we want staging verification.
2. Watch the new golden corpus for regressions in candidate selection and catastrophic calorie outliers.
3. Leave the unrelated dirty-tree noise alone: the existing cron/schema edits and migration in the workspace are not part of this change and should not be folded into it.
4. The earlier delegated-run Python 3.10 mismatch (`ImportError: cannot import name 'UTC' from 'datetime'`) was only a caveat during exploration; it is not the current validation result.
5. The full suite still has one unrelated dirty-tree cron/schema failure, and architecture checks also show unrelated dirty-tree failures. Those are outside this parse-text change and must stay separate.

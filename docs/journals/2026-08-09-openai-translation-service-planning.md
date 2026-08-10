# OpenAI Translation Service Planning

**Date**: 2026-08-09 12:47
**Severity**: Medium
**Component**: Translation architecture and cutover planning
**Status**: Resolved

## What Happened

We finished the brainstorm and deep-TDD planning pass for replacing DeepL runtime translation with a neutral OpenAI-backed translation stack. The approved direction was not “swap the provider”; it was a staged cutover: neutral contract first, then a dedicated OpenAI Responses adapter, then read-path cutover, then persisted meal and suggestion cutover, and only then DeepL removal. The final plan also locked the exact outcome rules, cache admission policy, rollback constraints, and the privacy boundary for translation requests.

The key decision was to keep a neutral `TextTranslationPort`/`TextTranslationService` boundary and bind it to a dedicated OpenAI translation adapter, instead of letting translation hide inside a generic AI router. That kept translation semantics explicit and avoided smearing provider fallbacks across unrelated AI behavior. The plan also forced `store=False` on translation calls, made barcode persistence canonical English only, split Phase 3 into a distinct getter so read paths would not break Phase 4 consumers, and defined source-shaped completeness so legacy persistence does not pretend every row is equally trustworthy.

## The Brutal Truth

This was a lot of policy to nail down before any code moved, and that is exactly why it matters. Translation cutovers tend to rot quietly if the contract is vague. The annoying part is that the hard decisions were not about “OpenAI vs DeepL”; they were about what counts as translated, what can be cached, what can be persisted, and what must fall back to canonical text. If we had skipped that, we would have shipped a mess that looked fine in happy-path tests and then poisoned caches or persisted partial garbage later.

## Technical Details

- Brainstorm: [260809-1149-openai-translation-service-brainstorm.md](../../plans/reports/260809-1149-openai-translation-service-brainstorm.md)
- Plan: [openai-translation-service-cutover/plan.md](../../plans/260809-1152-openai-translation-service-cutover/plan.md)
- Adjudication: [from-controller-to-planner-red-team-adjudication-proposal.md](../../plans/260809-1152-openai-translation-service-cutover/reports/from-controller-to-planner-red-team-adjudication-proposal.md)
- Red-team result: 15 deduped findings, 14 accepted, 1 rejected
- Locked rules: forced `store=False`, canonical English barcode persistence, distinct Phase-3 `get_text_translation_service`, translated-only non-English cache/persistence, source-shaped completeness, and rollback by retained cache namespace plus cutover timestamp
- Validation status: plan structure and status checks only; no production code changed and no implementation tests or builds were run

## What We Tried

- Reread the brainstorm, plan overview, five phase files, and adjudication proposal
- Checked the plan for consistency across cache policy, persistence boundaries, and rollback scope
- Confirmed the accepted/rejected red-team outcomes were propagated into the phase files

## Root Cause Analysis

The original risk was architectural drift: vendor-shaped translation semantics, cache admission rules, and persistence rules were all mixed together. That makes it too easy to blur presentation-only translation with durable storage. The plan fixed that by splitting the contract, the adapter, the read path, and the write path into separate phases.

## Lessons Learned

- Translation needs an explicit outcome model, not just a provider call.
- Cache admission and persistence must be outcome-aware or they will silently store fallback text.
- Barcode storage is a canonical-data problem, not a localization problem.
- Rollback has to account for retained cache namespaces and cutover timestamps when schema provenance is absent.

## Next Steps

- Implement Phase 1 through Phase 5 in order, with the accepted red-team corrections already baked into the scope.
- Keep DeepL runtime alive until the final deletion phase.
- Validate each phase with the requested focused tests before widening the gate.

## Unresolved Questions

None.

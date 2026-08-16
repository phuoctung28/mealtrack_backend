---
phase: 3
title: "Build Evaluation Harness And Release Gates"
status: completed
effort: "2-3 days"
---

# Phase 3: Build Evaluation Harness And Release Gates

## Overview

Build a parse-text-specific evaluation loop with hermetic CI fixtures and an
explicit live staging mode. Gate semantic accuracy and catastrophic
outliers before rollout; report latency and provider calls without logging PII.

**Priority:** P1
**Depends on:** Phase 2

## Context Links

- [Harness research](../reports/260814-1030-parse-text-harness-retrieval-research.md)
- [Phase 2](./phase-02-implement-structured-reference-resolution.md)
- `src/domain/services/meal_analysis/prompt_eval_loop.py`
- `scripts/development/evaluate_meal_analyze_prompt_candidates.py`
- `tests/unit/domain/services/meal_analysis/test_prompt_eval_loop.py`
- `src/observability_connectors.py`

## Key Insights

- The existing vision prompt loop measures parse/schema success, not nutrition
  identity, reference selection, energy error, latency, or provider calls.
- One versioned corpus can drive offline CI and a smaller opt-in live slice.
- Runtime metrics must be low-cardinality; evaluation reports identify cases by
  synthetic ID, never by raw input or provider payload.

## Requirements

- Versioned non-PII corpus: Vietnamese/English, grams/count/ambiguous units,
  preparation variants, oils/sauces/drinks/staples/compound dishes, local hit,
  wrong-first, miss, timeout, and incomplete detail.
- Deterministic mode uses fake AI plus synthetic/recorded-and-scrubbed FatSecret
  fixtures, blocks network, and returns stable machine-readable results.
- Live mode requires authoritative `ENVIRONMENT=staging`, a separate
  `PARSE_TEXT_LIVE_EVAL_ENABLED=true`, and an explicit confirmation flag. Unset,
  development-default, CLI-supplied environment labels, and production all fail
  closed. Use only curated corpus text.
- Live runs require explicit caps: at most 25 cases, concurrency one, 50 total AI
  generations, 25 searches, 25 details, and five minutes wall clock. Stop before
  the next case when any budget is exhausted.
- Write reports with mode 0600 and no overwrite to an OS temp path by default.
  Explicit repository paths must already be git-ignored; reject tracked or
  unignored paths.
- Gates: response contract 100%; catastrophic outliers 0; identity+quantity
  >=95%; candidate selection >=95%; common-food reference resolution >=90%;
  invalid structured reference accepted 0.
- Report provider calls per item and p50/p95 latency before rollout. Do not turn
  unbaselined latency into a pass/fail threshold in the first release.
- Separately gate the production timeout contract with deterministic max-item,
  slow-provider, cancellation, and call-cap tests using the same timeout config
  as the handler. Live p95 remains reported rather than a first-release gate.
- Gate constants are versioned; do not lower them just to pass CI.

## Architecture And Data Flow

```text
golden JSON -> eval loop -> runner(handler + fixture providers OR live providers)
            -> per-case assertions -> aggregate quality gates
            -> JSON report + console summary (IDs/counts/percentiles only)
```

Keep scoring/aggregation in a small domain eval module; CLI handles arguments,
environment guard, dependency construction, and report output.

The evaluator proves handler semantics. Public response compatibility is a
separate 100% gate executed by authenticated and guest HTTP route tests; a
handler-only run must never claim API-contract proof.

## Related Code Files

Create:

- `src/domain/services/meal_text_nutrition_eval_loop.py`
- `scripts/development/evaluate_parse_text_nutrition.py`
- `tests/fixtures/parse_text_nutrition_golden_cases.json`
- `tests/unit/domain/services/test_meal_text_nutrition_eval_loop.py`
- `tests/unit/scripts/test_evaluate_parse_text_nutrition.py`

Modify:

- `docs/external-services.md` (preserve and merge current user edits)
- `docs/testing-standards.md`
- focused Phase 1/2 tests if the harness reveals an actual contract gap
- `.gitignore` only if a repository-owned eval-artifact directory is chosen;
  OS temp output requires no ignore change

No DB, route, response-schema, mobile, or image-analysis changes.

## Implementation Steps

1. **Tests Before:** define corpus schema tests and failing aggregate-gate tests
   for every approved metric, including potato 890 and wrong-first selection.
2. Add a typed case/result/summary model and pure evaluator for identity,
   quantity, selected source, expected macro/calorie bounds, call counts, and
   duration. Percentiles must be deterministic for fixed inputs.
3. Add curated corpus v1 and staged provider fixtures. Case IDs encode category
   and locale but contain no user/person identifier.
4. Implement offline runner with network-disabled fakes and explicit counters
   for AI, candidate search, and detail calls.
5. Implement live mode with the authoritative staging/enable/confirmation gates,
   fixed aggregate budgets, case filtering, concurrency one, and total deadline;
   default remains offline and no CLI label may establish environment trust.
6. Emit JSON safely to OS temp or a verified ignored path and a concise console
   table. Use exclusive 0600 creation and refuse overwrite. Never emit
   raw text, prompts, candidate bodies, credentials, or full provider errors.
7. **Refactor:** share scoring/gate logic between modes; do not duplicate the
   production resolver or call the image prompt evaluator.
8. **Tests After:** cover malformed corpus, network attempt, unset/development/
   production guards, false CLI environment labels, run budgets,
   secret/redaction invariant, threshold failure exit code, JSON schema, p50/p95,
   provider-call bounds, unsafe output paths, permissions, and no-overwrite.
9. Document exact offline/live commands, credential expectations, output policy,
   and rollback/degraded behavior. Merge around existing dirty docs changes.
10. Run the offline harness and focused suites; run live staging manually only
    when credentials and non-production environment are explicitly configured.
11. Run authenticated and guest HTTP contract suites as the 100% public-contract
    gate; keep their result distinct from handler/corpus metrics.
12. **Regression Gate:** run CI-aligned unit tests and architecture checks. Keep
    live provider proof separate from local/CI proof.

```bash
pytest tests/unit/domain/services/test_meal_text_nutrition_eval_loop.py tests/unit/scripts/test_evaluate_parse_text_nutrition.py -v
python scripts/development/evaluate_parse_text_nutrition.py --mode offline --output /tmp/parse-text-eval.json
pytest tests/unit --cov=src --cov-fail-under=65
pytest tests/architecture -v
ruff format --check src/ tests/ scripts/development/evaluate_parse_text_nutrition.py
ruff check src/ tests/ scripts/development/evaluate_parse_text_nutrition.py
mypy src/
```

Optional, never CI:

```bash
PARSE_TEXT_LIVE_EVAL_ENABLED=true python scripts/development/evaluate_parse_text_nutrition.py --mode live --confirm-live-staging --max-cases 25 --output /tmp/parse-text-live-eval.json
```

## Todo List

- [x] Define versioned corpus and result schema.
- [x] Write failing gate/percentile/privacy tests.
- [x] Build hermetic offline evaluator and CLI.
- [x] Add guarded live staging mode.
- [x] Enforce live budgets and safe report paths.
- [x] Run separate authenticated/guest public-contract gate.
- [x] Document and run offline release gates.
- [x] Record live evidence separately when available.

## Success Criteria

- [x] Offline mode is deterministic, network-free, and passes every quality gate.
- [x] Potato 890 is a permanent catastrophic-regression failure.
- [x] Provider-call counts prove one search plus at most one detail per resolved
  provider miss.
- [x] Live mode cannot run when configured as production.
- [x] Reports contain only synthetic IDs, aggregates, sources, reason codes, and
  timings; no raw text or provider payload.
- [x] Max-item slow-provider tests prove the handler's shared request deadline,
  cancellation, concurrency, and aggregate call limits.
- [x] Focused, CI-aligned unit, formatting, lint, compile, and feature-owned
  type gates pass;
  live staging results are reported without being misrepresented as CI.
- Architecture validation remains separately documented because the current
  dirty tree has three unrelated transaction-allowlist/domain-service-threshold
  failures; no architecture failure is attributed to this sync.
- The composition-root module retains pre-existing mypy diagnostics outside
  the feature-owned modules; its runtime wiring is covered by the passing
  dependency and route tests.

## Risk Assessment

- **Corpus overfit:** include multilingual categories and failure injections;
  version changes with review.
- **Flaky live metrics:** never place live mode in CI; treat latency as baseline
  reporting until a representative staging sample exists.
- **Fixture drift:** keep adapter-shape contract tests and periodically compare a
  scrubbed staging sample without committing vendor/user payloads.
- **Docs conflict:** `docs/external-services.md` is already dirty; inspect and
  merge, never overwrite or revert the user's work.

## Security And Privacy

- Offline mode must fail if a network client is invoked.
- Live mode uses environment credentials but never prints or serializes them.
- Store reports only in OS temp or a caller-selected path verified as ignored;
  do not commit live artifacts or raw provider responses.

## Next Steps

Roll out only after offline gates pass and the staging report has been reviewed.
If candidate accuracy misses the gate, improve deterministic scoring/corpus; do
not add vector RAG or probabilistic adjudication without a new approved plan.

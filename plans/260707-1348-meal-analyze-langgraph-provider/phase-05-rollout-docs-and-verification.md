---
phase: 5
title: "Rollout, Docs, And Verification"
status: completed
priority: P1
effort: "0.5-1d"
dependencies: [4]
---

# Phase 5: Rollout, Docs, And Verification

## Context Links

- Rollout guide: `docs/guides/meal-analyze-fastpath-rollout.md`
- External services: `docs/external-services.md`
- System architecture: `docs/system-architecture.md`
- Code standards: `docs/code-standards.md`
- Testing standards: `docs/testing-standards.md`
- Architecture tests: `tests/unit/architecture/`

## Overview

Document and verify the graph rollout. Keep rollout env-only and reversible:
graph disabled by default, FatSecret validation disabled by default, no mobile
contract change.

## Key Insights

- Existing docs already describe provider routing and meal analyze fast-path flags.
- New graph flags should live beside the current meal analyze rollout story.
- Sentry observability must remain privacy-safe and provider-neutral.

## Requirements

- Functional: docs explain enable, canary, rollback, and failure behavior.
- Functional: verification covers graph disabled and enabled paths.
- Non-functional: architecture tests prevent future boundary drift.
- Non-functional: no raw images, raw URLs, raw provider payloads, prompts, auth, email, or food payloads in logs/metrics.

## Architecture

Rollout policy:

```text
default env
  AI_MEAL_ANALYZE_GRAPH_ENABLED=false
  AI_MEAL_ANALYZE_FATSECRET_VALIDATION_ENABLED=false

canary
  AI_MEAL_ANALYZE_GRAPH_ENABLED=true
  AI_MEAL_ANALYZE_FATSECRET_VALIDATION_ENABLED=false

validation canary
  AI_MEAL_ANALYZE_GRAPH_ENABLED=true
  AI_MEAL_ANALYZE_FATSECRET_VALIDATION_ENABLED=true
```

Rollback is env-only: disable graph flag.

## Related Code Files

- Modify: `docs/guides/meal-analyze-fastpath-rollout.md`
- Modify: `docs/external-services.md`
- Modify: `docs/system-architecture.md`
- Modify: `docs/code-standards.md` only if new boundary rule needs codifying
- Modify: `tests/unit/architecture/test_meal_analyze_graph_boundaries.py`
- Modify: `.importlinter` only if a new import contract is needed
- Read only: `docs/testing-standards.md`

## Tests Before

1. Add failing docs/architecture test for graph boundary if not already complete:
   - domain cannot import graph.
   - graph cannot import infrastructure provider SDKs directly.
   - graph cannot write SQL.
2. Add smoke test for app import with graph flags present.

## Refactor

1. Update rollout guide with graph flags and canary ladder.
2. Update external services docs:
   - LangGraph orchestration is internal.
   - OpenAI/Cloudflare remain provider route.
   - FatSecret validation is optional/reference-only.
3. Update system architecture data flow for sync graph path.
4. Add any final architecture guardrails.

## Tests After

1. Run focused handler/graph/FatSecret tests.
2. Run architecture tests.
3. Run broader unit suite if time permits.
4. Run lint/import checks.

## Implementation Steps

1. Update docs after code behavior is final.
2. Verify links and flag names match settings.
3. Run focused tests.
4. Run architecture tests with importlib mode if collection needs it.
5. Run broader quality commands.
6. Record any skipped tests and blockers.

## Todo List

- [x] Rollout guide updated.
- [x] External services docs updated.
- [x] System architecture updated.
- [x] Architecture guardrails complete.
- [x] Focused tests pass.
- [x] Broader verification run or documented blocker.

## Success Criteria

- [x] Docs match implemented flags and behavior.
- [x] Rollback path is a single env flag.
- [x] Graph and FatSecret validation are independently gated.
- [x] Verification commands pass or failures are documented with root cause.

## Risk Assessment

- Risk: docs promise behavior not shipped.
  Mitigation: update docs only after implementation and test pass.
- Risk: canary enables FatSecret and graph together, hiding root cause.
  Mitigation: staged rollout: graph first, validation second.
- Risk: architecture tests become brittle.
  Mitigation: test stable layer rules, not exact implementation filenames beyond graph package boundary.

## Security Considerations

- Review new logs and metrics for sensitive fields.
- Keep provider credentials and account IDs out of documentation examples.
- Do not publish real image URLs in tests/docs.

## Regression Gate

```bash
uv run pytest tests/unit/app/graphs tests/unit/app/services tests/unit/handlers/command_handlers/test_upload_meal_image_immediately_command_handler.py tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py -q
uv run pytest tests/unit/architecture -q --import-mode=importlib
uv run python -m compileall src tests
uv run ruff check src tests
```

## Next Steps

After this phase, run `/ck:plan red-team` before implementation if it was not
already run, then execute with:

```bash
/ck:cook /Users/alexnguyen/Desktop/Nut/mealtrack_backend/plans/260707-1348-meal-analyze-langgraph-provider/plan.md --tdd
```

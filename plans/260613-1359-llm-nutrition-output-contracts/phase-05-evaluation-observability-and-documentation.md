---
phase: 5
title: "Evaluation Observability And Documentation"
status: pending
effort: "0.5d"
---

# Phase 5: Evaluation Observability And Documentation

## Context Links

- Prompt eval loop: `src/domain/services/meal_analysis/prompt_eval_loop.py`
- Roadmap: `docs/project-roadmap.md`
- PDR: `docs/project-overview-pdr.md`
- Testing standards: `docs/testing-standards.md`
- Architecture docs: `docs/architecture/index.md`

## Overview

Make the new LLM boundary observable and documented. The goal is to know when AI
output quality is bad, not just avoid crashes.

Priority: P1.

## Requirements

- Prompt evaluation includes schema/semantic validation pass rate, not only
  parser success.
- Runtime logs distinguish:
  - provider outage.
  - structured-output parse failure.
  - semantic nutrition validation failure.
  - retry success.
  - retry exhausted.
- Logs include purpose, strategy, model when available, attempt count, and
  sanitized field paths.
- Project docs record the architecture decision and bug fix impact.
- Final verification covers source, tests, and static checks.

## Architecture

Observability should sit at orchestration boundaries, not inside domain value
objects. Domain models keep invariants; adapters/handlers record invalid AI
output rates and retry outcomes.

## Related Code Files

Modify:

- `src/domain/services/meal_analysis/prompt_eval_loop.py`
- tests for prompt eval loop under `tests/unit/domain/services/meal_analysis/`
- `docs/project-roadmap.md`
- `docs/project-overview-pdr.md`
- optionally `docs/architecture/index.md` or linked AI architecture docs if present

Create if needed:

- `tests/unit/domain/services/meal_analysis/test_prompt_eval_loop.py`

## Implementation Steps

1. Write failing prompt-eval tests:
   - candidate with schema-invalid payload scores lower than valid candidate.
   - result exposes validation success rate.
   - threshold enforcement can fail on validation rate separately from token cost.
2. Extend `PromptEvalResult` with validation metrics while preserving old fields
   where tests or callers use them.
3. Add sanitized logging in Phase 3/4 code paths if not already covered.
4. Update roadmap/PDR changelog entries with the final architecture fix.
5. Run focused tests.
6. Run final verification gate from `plan.md`.
7. Review docs impact and unresolved questions before implementation handoff.

## Success Criteria

- [ ] Prompt eval can detect schema/semantic failures.
- [ ] Invalid-output retry paths emit sanitized logs.
- [ ] Docs explain the contract-first LLM boundary and why parser filtering was not enough.
- [ ] Focused tests pass.
- [ ] Final verification gate passes or failures are documented with exact blockers.

## Risk Assessment

- Risk: Metrics become too broad for current telemetry stack. Mitigation: start
  with structured logs and prompt-eval fields; defer external metrics backend.
- Risk: Docs overstate provider guarantees. Mitigation: describe Gemini as a
  probabilistic extractor plus deterministic validation, not a trusted source.

## Security Considerations

- Observability must not store raw images, base64 payloads, or large meal text.
- Validation snippets should use field paths and short error codes.

## Next Steps

After this phase, prepare implementation summary and optionally create a focused
branch/PR if the user wants shipping workflow next.

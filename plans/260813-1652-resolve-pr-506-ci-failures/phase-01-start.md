---
phase: 1
title: "Resolve and Verify CI Failures"
status: in-progress
priority: P1
effort: "2h"
dependencies: []
---

# Phase 1: Resolve and Verify CI Failures

## Context Links

- PR: https://github.com/phuoctung28/mealtrack_backend/pull/506
- CI run: https://github.com/phuoctung28/mealtrack_backend/actions/runs/31660621297
- Related plan: `../260727-1905-slot-only-recommendation-replenishment/plan.md`

## Overview

Complete the beverage schema removal coherently, restore OpenAI strict-schema
compatibility, and correct stale catalog projection state.

## Requirements

- Keep drinks represented as normal `foods` entries.
- Reject legacy `beverage_metadata` as an extra field; do not silently restore
  packaged-beverage routing.
- Include every OpenAI object property in `required`, including nullable fields.
- Prefer a reloaded ORM catalog relationship over transient domain fallback data.
- Preserve API shapes, persistence schema, macro-derived calories, and meal routing.

## Architecture

Pydantic owns the provider-independent vision contract. The OpenAI adapter only
normalizes that schema into OpenAI's supported subset. Recommendation rows may
carry transient domain meals before flush, but loaded relationship state is the
authority after reload.

## Related Code Files

- Modify: `src/domain/model/ai/nutrition_contracts.py`
- Modify: `src/infra/services/ai/langchain_openai_adapter.py`
- Modify: `src/infra/repositories/meal_recommendation_plan_repository_async.py`
- Modify: `tests/unit/domain/model/ai/test_nutrition_contracts.py`
- Modify: `tests/unit/domain/services/prompts/test_prompt_constants.py`
- Modify: `tests/unit/handlers/command_handlers/test_beverage_scan_routing.py`
- Modify: `tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py`

## Implementation Steps

1. Remove the now-unused `BeverageMetadata` type and update contract tests to
   assert `extra_forbidden` rather than the deleted validator message.
2. Remove obsolete `beverage_metadata: null` from successful handler fixtures
   and make the prompt assertion wording-independent.
3. Remove nullable-property filtering from OpenAI schema normalization so each
   object's `required` set equals its property set.
4. Change catalog projection precedence to use loaded `catalog_meal` first and
   `_domain_catalog_meal` only when no relationship value is available.
5. Run focused tests, Ruff, compilation, then the CI-aligned unit suite.
6. Review the final diff, commit, push the PR branch, and recheck Actions.

## Todo

- [ ] AI contract and fixtures aligned
- [ ] OpenAI strict schema valid
- [ ] Recommendation projection failure fixed
- [ ] Focused and full validation green
- [ ] Review complete and PR checks green

## Success Criteria

- Seven original failed nodes pass.
- Unit suite reports zero failures and coverage remains at least 65%.
- No Ruff or compilation errors in touched files.
- GitHub Actions required checks pass.

## Risk Assessment

- Risk: loaded SQLAlchemy relationships may be absent before reload. Mitigation:
  retain `_domain_catalog_meal` as the fallback.
- Risk: test edits could hide beverage regression. Mitigation: retain explicit
  rejection tests and end-to-end meal-routing assertions.
- Rollback: revert the fix commit; no migration or external state change.

## Security Considerations

No auth, secrets, personal data, or external input surface changes.

## Next Steps

No follow-up required once CI is green. The active replenishment plan remains
independent and should preserve the projection precedence invariant.

---
type: validation
date: 2026-07-16
plan: ../plan.md
status: complete
---

# Validation: Catalog Meal Recommendation Decisions

## Summary

Seven implementation-blocking decisions confirmed with the user. No additional codebase verification repeated because `plan.md` already contains an evidence-backed full-tier red-team review and no `[UNVERIFIED]` tags.

## Questions and Answers

1. **[Catalog rights]** What exact owned/licensed source will supply the initial Vietnamese, Japanese, and Korean recipe catalog, and who owns acquisition and rights approval?
   - Options discussed: commissioned owned/licensed corpus | approved supplemental licensed sources.
   - **Answer:** Nutree commissions 180 recipes: 60 Vietnamese, 60 Japanese, 60 Korean. Product/Content Acquisition owns sourcing and delivery. Founder/CEO or authorized company signatory, advised by IP counsel, approves rights. Engineering publishes only recipes with approved rights records. TheMealDB and CC-licensed sources are supplemental only after separate approval.
2. **[Allergy scope]** For users whose profiles contain allergies, should MVP block catalog recommendations entirely, or allow them with `allergy_evaluated: false` disclosure?
   - Options: block allergy-bearing profiles | disclosure-only behavior.
   - **Answer:** Ignore allergies for MVP. No filtering or blocking; disclose `allergy_evaluated: false`; make no safety claim.
3. **[Regeneration]** Should regeneration create a new plan, mark the previous active plan `superseded`, and retain it as immutable history?
   - Options: supersede and retain | mutate active plan | delete prior plan.
   - **Answer:** Supersede and retain.
4. **[Target window]** Should MVP disable client calorie overrides, accept `start_date` from today through seven days ahead, and snapshot one backend-resolved target for all three days?
   - Options: recommended bounded contract | allow override | date-specific recomputation.
   - **Answer:** Use the bounded contract.
5. **[Measurement]** Should MVP use only server-owned `plan_shown`, `alternatives_shown`, `swap_selected`, and `meal_logged` events?
   - Options: server-owned events | client viewed-event ingestion.
   - **Answer:** Server-owned events only.
6. **[Publishing]** Should MVP use a reviewed version-controlled seed/import pipeline with atomic activation and no admin publishing UI/API?
   - Options: seed/import only | admin workflow.
   - **Answer:** Seed/import only.
7. **[Rollout]** Should rollout use a hard environment kill switch, internal allowlist, deterministic server-side cohort assignment, and analytics-only PostHog?
   - Options: server-side access control | PostHog-controlled access | global boolean only.
   - **Answer:** Server-side access control.

## Confirmed Decisions

- Commissioned 180-recipe corpus with approved rights record per publishable recipe.
- Allergy filtering deferred without blocking; explicit disclosure required.
- Regeneration supersedes and retains immutable history.
- No client calorie override; start date is local today through +7 days; one target snapshot.
- All authoritative events are server-owned.
- Seed/import publishing only; no admin workflow.
- Hard kill switch plus internal allowlist and deterministic cohort assignment.

## Impact on Phases

- Phase 1: contract decisions closed.
- Phase 3: corpus, rights ownership, counts, and publishing workflow locked.
- Phase 5: regeneration, target, and start-date rules locked.
- Phase 7: client event ingestion removed; rollout evaluator and server events locked.

## Unresolved Questions

None.

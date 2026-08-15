---
phase: 3
title: "Normalize Search and Source Resolution"
status: completed
effort: 2d
---

# Phase 3: Normalize Search and Source Resolution

## Context Links

- [Backend research](./research/backend-contract-and-persistence.md)
- `src/app/handlers/query_handlers/search_foods_query_handler.py`
- `src/domain/services/food_mapping_service.py`
- `src/infra/repositories/food_reference_repository_async.py`
- `src/app/handlers/command_handlers/parse_meal_text_handler.py`

## Overview

Priority P1. Return additive, normalized nutrition and one logical source origin from food search and parse-text. Local results must be both verified and integrity-valid; provider identity must be namespaced and opaque.

## Key Insights

- Current local search ranks verified rows but does not make integrity validity a hard predicate.
- Search may return `food_reference_id`, but parse DTOs and Flutter lose it.
- Provider search and parse use different resolution depth; they must share policy and normalization without duplicating provider calls.

## Requirements And Architecture

- Add `origin`, `food_reference_id`, namespaced `food_id`, nutrition basis/version, backend `calories_per_100g`, and normalized serving options without removing old keys.
- Add nullable canonical `source_namespace` and opaque `source_food_id` to `food_reference`; persist the repository's existing `external_id`, project it through reads, and enforce a partial unique `(source_namespace, source_food_id)` identity when both are present. Upsert resolves source identity before normalized name; a source/name collision enters review rather than overwriting. Legacy rows remain explicitly unknown rather than inferred from names.
- Treat source identity as one logical tagged origin. Existing `food_id=food_reference:<id>` is a deprecated response alias when it matches `food_reference_id`; a mismatching alias is rejected. Versioned save requests send only the dedicated canonical field.
- Exclude hard-invalid local rows by evaluating the shared policy at read time; semantically suspicious rows route to review, not silent substitution. Phase 6 materializes integrity state after a guarded audit.
- Version/invalidate cached result payloads where additive schema or normalized serving values are cached.
- Preserve provider outage degrade behavior and route latency budgets.
- Apply runtime integrity filtering before final dedupe/limit; overfetch until the requested valid-result limit is filled or candidates are exhausted.

## Related Code Files

Modify:

- `src/app/handlers/query_handlers/search_foods_query_handler.py`
- `src/domain/services/food_mapping_service.py`
- `src/infra/repositories/food_reference_repository_async.py`
- `src/domain/ports/food_reference_repository_port.py`
- `src/app/schemas/meal_schemas.py`
- `src/api/schemas/response/meal_responses.py`
- `src/app/handlers/command_handlers/parse_meal_text_handler.py`
- `src/api/routes/v1/meals_manual_text.py`
- `src/infra/database/models/food_reference_model.py`
- existing search/cache/parse tests

Create:

- `tests/integration/api/test_parse_text_identity_contract.py`
- timestamped canonical provider-provenance migration and migration tests

## TDD Implementation Steps

1. Add failing API tests for local canonical identity, namespaced provider identity, old-client additive compatibility, and logical exact-one-origin validation, including matching and mismatching local aliases.
2. Add failing cases for invalid verified rows being absent, normalized `g=1`, a labelled `100 g` serving, Vietnamese queries, and provider outage.
3. Add migration/repository tests proving provider identity round-trips, deduplicates by namespace plus ID, and leaves legacy identity unknown.
4. Overfetch local projections, filter through the shared policy, then dedupe/limit so invalid high-ranked rows cannot crowd out valid results.
5. Normalize provider detail into the same per-100g and serving contract.
6. Carry canonical/provider identity through parse DTO and response; reuse PR #509 resolution rather than copy it.
7. Version affected caches by response schema and active integrity-policy version; verify no cross-schema/policy stale hit. Phase 6 adds transition generation invalidation.

## Verification

- `pytest tests/unit/handlers/query_handlers/test_search_foods_partial_cache.py tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py tests/unit/api/test_guest_parse_trial.py -v`
- `pytest tests/integration/routes/test_foods_api.py tests/integration/api/test_parse_text_identity_contract.py -o addopts='' -v`
- `python scripts/development/evaluate_parse_text_nutrition.py --mode offline`
- Staging smoke: English/Vietnamese, local/provider, provider outage, warm/cold cache.

## Success Criteria

- [x] Structured results carry one logical durable origin and backend calorie density; compatibility aliases cannot disagree.
- [x] Invalid verified rows cannot surface through local search.
- [x] `g=1` and labelled 100g serving behavior are contract-tested.
- [x] Canonical provider namespace/ID provenance persists and deduplicates independently of normalized display name.
- [x] Old clients ignore additive fields without failure.

## Completion Evidence

- Added the additive origin, namespace, opaque source ID, nutrition basis/version, and backend calorie-density fields through search mapping, parse DTOs, and API responses.
- Added `food_reference.source_namespace` and `food_reference.source_food_id` with a partial unique identity index; repository upserts check source identity before normalized-name conflict and leave legacy rows nullable.
- Local search applies the shared integrity policy before namespace-aware dedupe and limit, continuing candidate batches until valid results fill the limit or candidates are exhausted; cache keys include both the response schema and active integrity-policy version.
- Provider parse results without a durable opaque source ID now degrade to the AI path instead of claiming provider authority; source-identity renames remain review collisions.
- Focused Phase 3 and compatibility verification: `71 passed` across identity, search, repository, adapter, parse, and food API tests; filtered unit gate: `2327 passed, 1 deselected`, coverage `79.55%`; offline evaluator: `10` synthetic cases passed.
- Full unit gate still has one unrelated failure in `tests/unit/cron/test_push_cron.py::test_push_cron_phase_failure_does_not_abort_subsequent_phases` caused by local onboarding claim-promotion WIP; no Phase 3 test fails.

## Risks, Security, And Rollout Gate

- Risks: stale cache payloads and search latency. Mitigate with cache versioning and before/after latency evidence.
- Security: provider IDs remain namespaced opaque values; logs contain no queries or food payloads.
- Gate: staging compatibility and outage/degrade proof before save-path authority changes.

## Unresolved Questions

None.

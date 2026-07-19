# Red-Team Security Adversary Plan Review

## Scope And Verdict

Reviewed `plan.md` and Phases 1-7 only; live code used solely to fact-check attack plausibility. No plan/code edits. **Block implementation until the High findings are resolved in the contract.**

## Findings

### 1. HIGH — Allergy-bearing users can receive contraindicated recipes

- **Plan location:** Phase 1, Requirements/Security (`phase-01-contract-and-regression-lock.md:30,66-68`); Phase 4, Requirements/Implementation (`phase-04-deterministic-recommendation-domain.md:26-29,44-51`); Phase 5, Requirements (`phase-05-durable-plans-cqrs-and-api.md:26-29`).
- **Plan flaw:** Freezing `allergy_evaluated=false` avoids a claim but does not prevent harm. Candidate retrieval/scoring has no allergen metadata, exclusion rule, or gate for allergy-bearing users.
- **Failure scenario:** A profile contains `shellfish`; the optimizer recommends shrimp because it satisfies cuisine/calorie constraints. The UI presents a personalized recommendation, the user acts on it, and suffers a reaction. An “unevaluated” flag is disclosure, not a safety control.
- **Codebase evidence:** Allergies are persisted as first-class profile data (`src/infra/database/models/user/profile.py:81-90`) and returned to application logic (`src/app/handlers/query_handlers/get_user_profile_query_handler.py:99-108`). Existing suggestion logic explicitly filters them (`src/domain/services/suggestion/suggestion_service.py:171-201`), while existing insight guidance says never recommend conflicting foods (`src/domain/services/meal_value_insight_service.py:322-323`).
- **Required correction:** Either block the MVP for all profiles with non-empty allergies, or add normalized allergen/cross-contact metadata, conservative exclusion, publication validation, profile snapshotting, and tests. Keep `allergy_evaluated=false` only as additional disclosure.

### 2. HIGH — Unverified/poisoned seed nutrition can become an immutable calorie authority

- **Plan location:** Phase 2, Requirements/Implementation (`phase-02-canonical-ingredient-and-nutrition-foundation.md:26-29,45-51`); Phase 3, Requirements/Architecture/Implementation/Security (`phase-03-immutable-curated-recipe-catalog.md:26-33,46-53,70-72`).
- **Plan flaw:** Publication requires a resolvable `food_reference`, complete macros, schema-valid version-controlled JSON, and allowlisted URLs, but never requires `food_reference.is_verified`, an approved source, artifact integrity, publisher authorization, or a source/image URL policy precise enough to prevent hostile content. Resolution and idempotency do not establish trust.
- **Failure scenario:** A compromised contributor or seed artifact supplies schema-valid but false macros/density plus an attacker-controlled image/source URL. Import succeeds; an immutable recipe version derives authoritative calories from poisoned macros and distributes hostile media. Logged meals and weekly budgets inherit the false calorie values.
- **Codebase evidence:** The canonical model explicitly separates `source` and `is_verified` (`src/infra/database/models/food_reference_model.py:53-56`), proving rows have different trust levels. The existing importer accepts all JSON in a caller-selected directory (`scripts/import_food_seeds.py:115-129`), validates only narrow macro/name checks (`scripts/import_food_seeds.py:44-60`), then passes entries directly to upsert (`scripts/import_food_seeds.py:141-155`). Calories are mechanically derived from macros (`src/domain/model/nutrition/macros.py:29-36`). Existing secure URL handling uses parsed exact `https` scheme/host checks (`src/api/routes/v1/meals.py:145-150`), whereas “allowlisted” is not specified to that level in the plan.
- **Required correction:** Require verified approved-source references for publication; use strict per-field bounds; validate source/image URLs by parsed scheme, exact host, path, redirects, and content policy; separate import from publish; require an approved manifest digest and publisher identity; record append-only import/publish audit data.

### 3. HIGH — Idempotency is neither tenant-safe nor abuse-bounded

- **Plan location:** Phase 5, Requirements/Architecture/Implementation (`phase-05-durable-plans-cqrs-and-api.md:26-33,47-54`); Phase 6, Implementation Steps 1-2 (`phase-06-transactional-swap-and-meal-logging.md:44-48`).
- **Plan flaw:** “Owner/idempotency lookup,” “unique swap request ID,” and fingerprints do not freeze uniqueness scope, authorization-before-replay ordering, key bounds, or retention. Fresh keys bypass dedupe, while superseded history retains a plan plus 9 slots and 45 alternatives per success.
- **Failure scenario:** Two users submit predictable `mobile-retry-1`; a global unique key causes cross-tenant denial or leaks the first user's stored replay if lookup precedes ownership. Separately, one valid account submits thousands of fresh keys, amplifying CPU and durable rows while complying with the stated contract.
- **Codebase evidence:** Server-resolved identity comes from `get_current_user_id` (`src/api/dependencies/auth.py:154-187`) and existing routes insert it into commands (`src/api/routes/v1/meal_suggestions.py:60-95,185-215`). There is no generic request-idempotency primitive that makes the missing scope implicit. Existing expensive suggestion endpoints are rate-limited to `5/minute` (`src/api/routes/v1/meal_suggestions.py:60-66,185-191`) through `src/api/middleware/rate_limit.py:12-35`; the new route plan never requires an equivalent control.
- **Required correction:** Define uniqueness as `(authenticated_user_id, operation, idempotency_key)`; forbid owner fields in request bodies; canonicalize/version fingerprints; authorize before replay; cap key length; rate-limit create/swap/log; serialize active generation per owner; define superseded-plan retention; test same-key cross-user/cross-operation and fresh-key flooding.

### 4. HIGH — Sensitive analytics contradict the plan's “no user IDs” rule

- **Plan location:** Phase 7, Architecture/Security (`phase-07-measurement-and-controlled-rollout.md:32-35,70-72`).
- **Plan flaw:** The plan requires user-action funnels while prohibiting user IDs, but defines no pseudonymous identifier, consent/opt-out, retention/deletion, or per-event property allowlist. Existing PostHog capture necessarily sends a stable `distinct_id`.
- **Failure scenario:** Implementation follows the existing adapter and sends Firebase UID/database UUID for `plan_viewed`, `alternative_viewed`, `swap_selected`, and `meal_logged`. PostHog gains a durable linkable trail of meal behavior despite the plan promising no user IDs.
- **Codebase evidence:** `PostHogAdapter.capture` requires and transmits `distinct_id` (`src/infra/adapters/posthog_adapter.py:23-42`); current lifecycle analytics uses Firebase UID or DB user ID (`src/api/routes/v1/webhooks.py:454-480`). Operational observability also allowlists `user_id` and `image_url` (`src/observability_connectors.py:8-45`), so a generic bounded-attributes statement cannot protect every sink.
- **Required correction:** Define sink-specific contracts: rotated/HMAC pseudonymous PostHog ID or explicit stable-ID approval, consent/opt-out, retention/deletion, environment separation, strict event property allowlists, and adapter tests rejecting forbidden fields. Define operational logs/metrics separately.

### 5. MEDIUM — Client-owned view events are forgeable and can poison rollout decisions

- **Plan location:** Phase 1, Implementation Step 1 (`phase-01-contract-and-regression-lock.md:43-47`); Phase 7, Requirements/Implementation Step 2 (`phase-07-measurement-and-controlled-rollout.md:27-30,45-49`).
- **Plan flaw:** Owning a plan/slot ID proves authorization, not that an exposure occurred. Unspecified client dedupe keys can be rotated indefinitely. No ingestion schema, event order/state rule, or server-issued exposure binding is planned.
- **Failure scenario:** A scripted authenticated client sends unlimited `plan_viewed`/`alternative_viewed` events with fresh dedupe keys against one owned plan. Funnel metrics inflate and drive an unsafe cohort expansion or false product conclusion.
- **Codebase evidence:** The current adapter forwards caller-provided event names/properties directly to PostHog (`src/infra/adapters/posthog_adapter.py:23-42`) with no schema, ownership, sequence, or dedupe control. Base domain events document generated IDs/correlation metadata but provide no authenticity mechanism (`src/domain/events/base.py:38-52`).
- **Required correction:** Record exposures server-side when plans/alternatives are returned. If client telemetry remains, require a dedicated authenticated schema, server-issued signed exposure token, `(user, exposure, event_type)` uniqueness, bounded timestamp/order, rate limits, and separation of untrusted telemetry from authoritative rollout metrics.

## Severity Summary

- Critical: 0
- High: 4
- Medium: 1

## Unresolved Questions

- Exclude all allergy-bearing profiles in MVP, or implement allergen metadata now?
- May PostHog use stable pseudonymous identity, and what retention/deletion contract applies?
- Who may approve/publish a catalog seed artifact, and what superseded-plan retention is required?

**Status:** DONE
**Summary:** Reviewed all eight plan files; retained the five strongest evidence-backed security flaws without editing the plan.
**Concerns/Blockers:** Four High findings should block implementation until contract changes are approved.

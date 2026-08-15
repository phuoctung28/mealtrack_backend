---
phase: 6
title: "Quarantine Data and Release Safely"
status: completed
effort: 3d
---

# Phase 6: Quarantine Data and Release Safely

## Context Links

- [Production audit and rollout research](./research/data-quality-rollout.md)
- food-reference parent/serving models and repository
- protected catalog approval/import routes and reviewer service
- food search handler/cache adapter
- `migrations/README.md`

## Overview

Priority P1. Materialize versioned integrity eligibility, invalidate stale caches, and quarantine hard-invalid rows through attributable compare-and-swap operations. Do not silently rewrite plausible-but-ambiguous food identities or erase editorial verification.

## Key Insights

- Production has 2,142 references and verified catastrophic rows; `is_verified` alone is unsafe.
- Serving conversions are child rows and can change without reliably changing the parent timestamp.
- Warm Redis search results bypass repository eligibility for up to one hour.
- Policy upgrades, quarantine, restore, and child edits must all invalidate materialized eligibility and caches.

## Requirements And Architecture

### Versioned Eligibility And Cache Coherence

- Preserve editorial `is_verified`; add `integrity_status` (`unknown`, `valid`, `quarantined`), `integrity_policy_version`, checked timestamp, reason, canonical policy-input digest, and review reference.
- Add one durable DB control row containing active policy version, catalog-integrity generation, activation run/revision, and update timestamp. Runtime configuration declares supported policy implementations only; replicas fail closed if the DB activates an unsupported version.
- Public eligibility joins the DB control row: `is_verified AND integrity_status='valid' AND integrity_policy_version=control.active_policy_version`.
- A new policy cannot activate until complete reclassification/parity; final activation atomically verifies the cohort, updates the control row, and advances generation. Restore reruns the DB-active policy and creates a new forward transition.
- Food-search reads the DB control row before cache lookup; keys include response schema, active policy, and generation. Every state transition advances generation in the same DB transaction, then invalidates old namespaces after commit. Cache hits batch-recheck canonical IDs. Redis unavailable means cache miss, never stale in-memory fallback.

### Parent And Serving Integrity

- Before normalized-serving cutover, manifest CAS digest covers parent nutrition/density/identity, legacy serving JSON, and deterministically ordered serving rows. `updated_at` alone is insufficient.
- All parent/child writers take the same per-reference transaction advisory lock in deterministic ID order.
- Child DB checks require at least one finite positive grams/milliliters conversion and canonical `g` exactly 1 gram. Any serving insert/update/delete invalidates parent integrity state/version at the database boundary and inserts a system transition event until the application revalidates after child synchronization.
- Backfill legacy serving JSON to child rows, normalize `g=1`, prove JSON/child parity, stop application JSON fallback/writes, and clear legacy JSON for V1-classified rows. V1-valid constraint prohibits legacy serving JSON; unknown legacy rows may retain it until reviewed.
- Identical V1 boundary fixtures execute against domain policy, audit classifier, parent checks, child checks, and invalidation trigger.

### State Machine And Audit Ledger

- Every approval/import/barcode/upsert writer transitions integrity atomically; setting `valid` runs active policy in the same UoW. Only reviewed quarantine may retain editorial verification with invalid nutrition.
- Append-only event fields: food-reference ID, before/after status, reason, policy version, input digest, actor kind, HMAC reviewer principal or fixed system actor, approval reference, run UUID, operation ID, manifest SHA-256, deployed revision, and timestamp. No nutrition payload or PII.
- Database permissions/trigger reject event UPDATE/DELETE. Application rollback never drops the ledger; empty-test-schema downgrade coverage must not imply production audit deletion is safe.
- Parent/child writers set transaction-local operation, actor, and deployed-revision audit context; integrity triggers reject protected mutations when required context is absent.
- Quarantine locks rows/children, recomputes digest, compare-and-swaps the entire batch, and aborts on drift. Restore requires the recorded transition/current digest and active-policy pass.

### Migration And Sunset

- Split additive state/ledger/generation schema from later parent/child checks and validation. Use short `lock_timeout`, bounded `statement_timeout`, long-transaction preflight, safe retry, `NOT VALID`/`VALIDATE` where supported, and record lock/query-plan evidence. Add a verified-valid partial index only if `EXPLAIN` shows the new predicate materially regresses search.
- Contract/app/platform headers classify attempts before Pydantic; missing contract header is legacy and malformed/schema-rejected requests remain in counts. Exact legacy rate is legacy authenticated create/edit attempts divided by all authenticated create/edit attempts.
- Telemetry completeness is classified pre-validation attempts divided by authenticated create/edit access-log requests, with outcome responses divided by classified attempts as a second check; both must be at least 99%.
- Active-device adoption comes from existing PostHog `app_open` events: distinct anonymous devices active in the trailing 14 days, grouped by app version/platform; no device IDs enter plan artifacts. Legacy removal—not additive rollout—requires for 14 consecutive days: legacy rate below 0.5%, at least 500 attempts, both completeness checks at least 99%, v2-capable versions at least 99% of active devices, release age at least 30 days or two cycles, zero integrity regressions, and force-update readiness. Removal remains separately approved.

## Related Code Files

Create:

- read-only integrity audit CLI and dry-run-default quarantine/restore CLI
- integrity event and catalog-generation models/repositories
- single-row integrity policy control model/repository
- parent/child state/constraint/append-only migration tests
- release runbook with manifest, lock, cache, dashboard, rollback, and approval evidence

Modify:

- food-reference parent/serving models, projections, repository, and every verification writer
- catalog admin route/service to pass authenticated reviewer identity safely
- food search/cache key/port/adapter and observability allowlist/tests
- runtime-supported policy registry, audit-principal HMAC salt, and bounded lock timeouts
- `docs/external-services.md`

## TDD Implementation Steps

1. Run the shared V1 boundary fixtures through audit and SQL parent/child enforcement; add single-control-row, rolling-replica unsupported-version, and atomic activation/reclassification tests.
2. Add parent/legacy-JSON/child lock/digest tests, including JSON-to-child parity/backfill, fallback removal, concurrent serving correction, direct child invalidation, deterministic multi-ID ordering, and stale digest abort.
3. Add state-machine tests for catalog approval, barcode, import, upsert, policy upgrade, quarantine, and active-policy restore.
4. Add append-only ledger tests for attribution fields and rejected UPDATE/DELETE; test application rollback preserves ledger.
5. Add warm-cache -> quarantine -> hidden, restore -> visible, and policy-upgrade -> old-cache-miss integration tests.
6. Add migration lock-timeout, long-transaction, upgrade/empty-downgrade, validation, query-plan, and optional partial-index evidence tests.
7. Run read-only aggregate audit and versioned manifest dry run. Live production mutation requires separate operations approval; once approved, execute guarded CAS batches and record before/after/deployed-revision evidence.
8. Prove read-time policy versus materialized eligibility parity, activate V1/generation, then release Flutter after cache and direct-save gates pass.
9. Build the `Manual Nutrition Authority` dashboard from pre-validation headers/access logs plus PostHog active-device adoption; test exact formulas and keep sunset as a separate change.

## Verification

- Audit/quarantine/state/cache/ledger tests and migration upgrade/empty-downgrade tests.
- Targeted PostgreSQL concurrency/trigger/constraint integration and `./scripts/development/migrate.sh test`.
- `pytest tests/unit --cov=src --cov-fail-under=65`, `lint-imports`, and query-plan comparison.
- Staging old/v2 clients, provider outage, warm cache, direct stale ID, local/provider/custom/override, Vietnamese search.
- Read-only Neon after-check and physical-device create/edit/barcode evidence; deployed revisions reported separately.

## Success Criteria

- [x] Pending control rows preserve legacy verified reads; after atomic activation, eligibility matches the active policy version and stale policy/cache entries cannot surface.
- [x] Parent and serving races invalidate or block stale valid state.
- [x] Quarantine/restore is attributable, append-only, reversible by forward transition, and CAS-safe.
- [x] Every verification writer and direct save uses active versioned eligibility.
- [x] DB checks reject future V1-invalid parent/serving writes and bounded migration evidence is covered by tests and disposable PostgreSQL smoke.
- [ ] Legacy sunset uses attempts plus adoption/completeness gates and cannot hide rejected old clients.

## Implementation Evidence

- Closed 2026-08-15 on `feature/canonical-nutrition-integrity-phase-06`.
- TDD coverage includes the versioned state machine, deterministic parent/legacy/child digest, stale-digest CAS rejection, append-only ledger, cache generation namespace, policy fail-closed behavior, migration source contracts, and CLI dry-run guardrails.
- Filtered CI-aligned unit gate passed: 2,384 tests, 78.44% coverage, excluding the unrelated pre-existing `tests/unit/cron/test_push_cron.py` WIP failure. The complete unit run remains 2,386 passed and one unrelated cron failure.
- `lint-imports` passed for 826 files and 3,752 dependencies; targeted Ruff and compile checks passed.
- Disposable PostgreSQL smoke applied migration `20260815000004`, exercised valid/quarantine/restore/child-invalidation/stale-CAS/constraint paths, and was dropped afterward. No production or shared database was mutated.
- Fresh-schema bootstrap now idempotently seeds the DB-owned control singleton after `Base.metadata.create_all()`; the regression suite and disposable PostgreSQL bootstrap smoke confirmed exactly one active-policy row.
- Public reads now remain compatible while `activation_run_id` is NULL and switch to strict materialized eligibility only after atomic cohort activation; verified/quarantined rows count as classified for activation completeness.
- `scripts/nutrition_integrity.py audit` is read-only; quarantine and restore default to dry-run and require an expected digest plus review reference for mutation.
- Staging, Neon, deployed-revision, physical-device, telemetry adoption, and the separately approved legacy-sunset gate remain release-operations evidence, not production actions performed by this cook run.

## Risks, Security, And Rollout Gate

- Risks: over-quarantine, child-row races, stale cache/version, lock duration, and premature sunset. Mitigate with shared fixtures, digest/advisory locks, generation keys, bounded migration locks, and separate approvals.
- Security: HMAC reviewer identity only in protected audit DB; no user data, food/query text, raw provider IDs, credentials, or DB URLs in telemetry/artifacts.
- Gate: all CI, migration, cache, staging, device, deployed-revision, and Neon evidence is recorded before unblocking dependent catalog work. Plan/cook never authorizes production mutation or destructive audit-ledger downgrade.

## Unresolved Questions

None.

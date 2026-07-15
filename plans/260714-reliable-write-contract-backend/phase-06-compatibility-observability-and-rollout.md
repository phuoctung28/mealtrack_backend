---
phase: 6
title: "Compatibility, Observability, and Rollout"
status: pending
priority: P1
dependencies: [0, 2, 3, 4, 5]
effort: "4-6 engineering days plus staged observation"
---

# Phase 6: Compatibility, Observability, and Rollout

## Overview

Prove failure semantics, compatibility, retention, privacy, and rollback before
enabling one action at a time. Elapsed time alone never advances rollout.

## HTTP Failure Semantics

| Admission/operation state | Mutation endpoint | Lookup | Re-execute? |
|---|---|---|---|
| Both operation fields absent | Legacy endpoint behavior | n/a | Legacy only |
| Partial/invalid/mismatched UUIDv4 | 400 `INVALID_IDEMPOTENCY_KEY` | `notFound` | No reservation |
| Flag off/version unsupported, no row | 409 `WRITE_CAPABILITY_DISABLED` | `notFound` | No |
| Flag off, existing pending row | 409 for new/reclaim; a live admitted owner may finish | `pending` + bounded `Retry-After` | Never resume stale work while off |
| Same key, changed fingerprint | 409 `IDEMPOTENCY_KEY_REUSED` | Owner sees state without fingerprint/body | No |
| Pending, live lease | 409 `OPERATION_IN_PROGRESS`, `Retry-After: 1..30` | `pending`, same bound | No duplicate owner |
| Pending, stale lease, flag on | CAS reclaim or 409 race result | `pending` | One fenced owner only |
| Committed | Exact original status + `rw-response-v1` JSON; replay true | `committed` + same frozen result | Never |
| Permanent deterministic failure | Exact original safe 4xx/body; replay true | `permanentFailure` + safe status/code/body | Never |
| Expired tombstone | 410 `OPERATION_EXPIRED` | `expired`, no fingerprint/result | Never; fingerprint is gone |
| Tombstone deleted | May become new only if capability is on | `notFound` | Mobile resends only if local created-at is within advertised retention |
| DB failure before reservation | 503 | `notFound` | Client follows retention/manifest rule |
| Transient failure after reservation | 503 safe body | `pending` until fenced reclaim or expiry | Only fenced reclaim while flag on |
| Response lost after commit | Transport ambiguity | `committed` exact result | Never |

Authentication/authorization runs before operation lookup/reservation. Never
convert an auth failure into a durable operation record. A server-generated 503
after commit is forbidden; projection/effect failures do not alter the committed
response. Transport loss remains possible and is reconciled. An expired
duplicate is always terminal and non-reexecuting because the fingerprint has
been privacy-scrubbed.

## Full Compatibility Matrix

| Mobile | Backend | Capability | Required result |
|---|---|---|---|
| Old | Old | n/a | Baseline |
| Old | New | ignored | Existing bodies/statuses; no operation row; known old-client blind-retry risk is not worsened |
| New | Old | manifest missing | Do not send operation fields or auto-retry; retain ambiguous local state |
| New | New | flag off/stale | One attempt, legacy contract; lookup remains enabled for old operation rows |
| New | New | flag on, v1 match | Durable operation + lookup; exact logical JSON/status replay v1 |
| New | New | unknown manifest/action version | Fail closed; no operation send/replay |
| Pre-migration backend process | Migrated DB | not advertised | Old process ignores table/flags; routes remain legacy |
| New backend process | Pre-migration DB | startup/predeploy failure | Do not serve enabled manifest; deployment fails before traffic |

New mobile must fetch/validate the manifest before adding body fields; old
Pydantic servers may ignore unknown JSON fields and headers without deduping.
Presence of accepted fields or an HTTP success never proves capability.

The shared staging suite runs old mobile/new backend and new mobile/old backend,
then new/new with each capability off/on and mobile contract v13. It verifies no
operation fields reach old backend, lookup remains usable after kill, exact
first/replay fixtures match, and unknown manifest/response versions fail closed.

## Observability and Retention

Phase 0 owns all mandatory pre-route redaction implementation and sentinel tests;
it completes before any Phase 1 migration or route deployment. This phase only
verifies that its redaction guarantees remain true under reliable-write fault and
rollout scenarios.

Use provider-neutral `src.observability` only. Metrics:

- `reliable_write.request.count`: action, outcome (`legacy|reserved|committed|replayed|conflict|pending|disabled|permanent_failure`);
- `reliable_write.duration_ms`: action, stage (`reserve|execute|lookup`), outcome;
- `reliable_write.pending.count` and `oldest_age_seconds`: action only;
- `reliable_write.expiry.count`: action, stage (`scrub|delete`).

Allowed logs: route template/action, enum outcome, contract version, retry flag,
bounded duration/count, exception class. Forbidden everywhere: raw/resolved UID,
operation ID or suffix, fingerprint, request/response/result body, entity ID,
meal/ingredient/image/value/timestamp, promo/referral code, token/header, URL,
receipt, payment details, or database error text containing values.

Create `src/cron/reliable_write_cleanup.py` using database time, bounded batches,
and `SELECT ... FOR UPDATE SKIP LOCKED`. It scrubs after 30 days, retains
seven-day expired tombstones, then deletes; effects expire only after terminal
and their parent operation policy permits it. Each row update predicates the
selected state/retention timestamp so replay/finalize races lose safely. Account
deletion cascade is tested concurrently. Cleanup is rerunnable and reports
counts only. A failure does not alter write capabilities but pages the named
owner before storage grows unbounded.
Provision an external Render cron command `python -m src.cron.reliable_write_cleanup`
after the entrypoint tests pass; schedule/owner belongs in deployment docs rather
than an in-process loop.

## Tests and Fault Injection

Create:

- `tests/integration/api/test_reliable_write_fault_injection.py`;
- `tests/integration/api/test_reliable_write_compatibility.py`;
- `tests/unit/cron/test_reliable_write_cleanup.py`;
- `tests/unit/architecture/test_reliable_write_guardrails.py`;
- `tests/unit/infra/monitoring/test_reliable_write_observability.py`;
- `tests/unit/api/middleware/test_reliable_write_request_redaction.py`;
- `tests/unit/api/test_reliable_write_exception_redaction.py`;
- `tests/unit/infra/monitoring/test_reliable_write_sentry_redaction.py`;
- `tests/integration/infra/test_reliable_write_sql_redaction.py` (also
  `@pytest.mark.postgres`);
- `tests/integration/app/test_reliable_write_lease_fencing.py`;
- `tests/integration/app/test_reliable_write_effect_repair.py`;
- `tests/integration/app/test_reliable_write_capability_cache.py`;
- `tests/contract/test_reliable_write_shared_fixtures.py`.

Inject faults: before reservation; after reservation; before socket response;
after external scan upload/AI; before domain flush; after domain flush/before
commit; after commit/before response; during cache invalidation/translation/
analytics; after effect delivery/before mark; during snapshot scrub; cleanup
versus replay/finalize/account deletion. Run two concurrent requests on separate
PostgreSQL sessions/process-like executors, including lease expiry while AI is
still running and two independent capability caches, not only mocked callbacks.

Architecture guardrails assert domain has no FastAPI/SQLAlchemy imports,
repositories never commit, routes do not instantiate handlers/UoWs, every
advertised action has route+handler+integration fixtures, and action registry
equals migration capability inventory and shared fixtures.

Versioned shared files are
`tests/fixtures/reliable_write/v1/{manifest,lookup,mutation,weight,benefits,fingerprint}.json`
and the identical mobile paths
`../mobile/test/fixtures/reliable_write/v1/{manifest,lookup,mutation,weight,benefits,fingerprint}.json`.
They cover every lookup status, first/replay/conflict/pending/expired/permanent
mutation response, every action including suggestion, all four weight outcomes,
partial/all-rejected batches, onboarding/promo/referral duplicate/conflict
decisions, exact UTC/Decimal strings, and canonical fingerprint cases. CI hashes
both copies, runs Python consumers here and Dart consumers in mobile, and fails
on drift.

Update `docs/system-architecture.md`, `docs/cqrs-guide.md`,
`docs/database-guide.md`, `docs/api-endpoints.md`, and deployment/cron guidance
with the final contract, retention, kill-switch, and rollback procedures.

## Rollout and Rollback

1. Deploy the instruction-authority corrections and mandatory route-template/
   Sentry/event-bus/SQL redaction. Do not expose lookup before redaction tests pass.
2. Run the real-PostgreSQL expand migration with every dedicated capability row
   false. Verify one Alembic head, ownership marker, tables/indexes/checks, false
   rows including suggestion, and `ever_enabled=false`; production cohort none.
3. Deploy web code containing manifest, ungated lookup, dedicated admin kill
   switch/cache, and **all** action integrations while every row remains false.
4. Provision the effect dispatcher and cleanup cron, run entrypoint tests and
   cleanup dry-run, and confirm effect backlog/expiry alerts with no user data.
5. Run old-client/new-backend staging smoke and legacy snapshots. Then validate
   new mobile against the shared manifest/lookup/response fixtures and full
   old/new/new matrix, including mobile contract v13. No flag changes yet.
6. After approvals, first enablement is global for one production action at a time
   in order: manual meal; suggestion; URL scan;
   food-label scan; multipart scan; meal edit/delete; weight sync/delete/create;
   onboarding; promo; referral. Each action has its own flag.
7. Advance only when named release owner approves numeric thresholds for
   duplicate prevention, conflicts, pending age, 5xx, latency, and lookup rate.
8. Kill switch: disable action row. Admission reflects off within 30 seconds;
   clients stop new sends/reclaims, a live admitted request may finish, and stale
   work never resumes. Existing records remain lookup-readable until retention.
9. App rollback is forward-only: disable all rows, deploy compatible prior code,
   and keep schema/data. Alembic downgrade is permitted only on a never-enabled,
   entirely unused install; it acquires the migration lock and aborts if
   `ever_enabled` or any operation/effect/attribution row exists.

## Verification Commands

```bash
uv run black src/ tests/
uv run ruff check src/ tests/
uv run mypy src/
uv run lint-imports
uv run pytest tests/unit --cov=src --cov-fail-under=65
uv run pytest tests/integration/api/test_reliable_write_fault_injection.py tests/integration/api/test_reliable_write_compatibility.py -o addopts="" -m integration
uv run pytest tests/integration/app/test_reliable_write_lease_fencing.py tests/integration/app/test_reliable_write_effect_repair.py tests/integration/app/test_reliable_write_capability_cache.py -o addopts="" -m integration
uv run pytest tests/contract/test_reliable_write_shared_fixtures.py
uv run pytest tests/migrations -m postgres
uv run alembic heads
```

From `../mobile`, run the mobile fixture/contract suite selected in its Phase 4
and Phase 5 plan, including contract v13; CI must also compare SHA-256 for the six
shared JSON fixture files. Run the staging matrix with capability off/on for each
action, but keep production rows false.

## Success Criteria

- [ ] Compatibility matrix and every fault boundary pass.
- [ ] No mutation can commit without same-transaction exact response and required effects.
- [ ] Kill switch disables new sends within manifest TTL while lookup remains.
- [ ] Observability redaction tests reject every forbidden field.
- [ ] Rollout owner, pause authority, minimum volume, and numeric thresholds are
  approved before any flag reaches production true.

## Remaining Decision Gates

- Mobile approves `rw-response-v1`: stored first-call status and exact logical
  JSON, including deterministic null optional meal projections and no rehydrate.
- Product/mobile approve operation-aware single same-instant weight upsert,
  partial batch, `rejected`, fixed UTC/Decimal, and synced-count semantics.
- Product/mobile approve onboarding `already_completed`, promo
  `already_redeemed`, referral `already_applied`, immutable user-unique attribution
  across internal/affiliate sources, and one-benefit behavior.
- Name rollout owner and pause authority; approve minimum observation volume and
  numeric duplicate/conflict/pending/5xx/latency/lookup thresholds.
- V1 has no production cohort or allowlist. First global enablement requires the
  named approvals; until then every action capability remains false.

## Validation Log

- Tier: Full (7 phases, Phase 0 through Phase 6).
- Fact check scope: reviewer-verified current route, command, handler, repository,
  model, migration, test, event-bus, and Alembic paths are cited; implementation
  must recheck the head and working tree before generating a revision.
- Flow trace: confirmed current concrete-UoW/manual-commit weight handlers,
  post-commit scan/translation boundaries, timestamp batch upsert, onboarding
  set-if-false, promo row lock/usage increment, referral business dedup, and
  promo/referral route handler bypasses.
- Contract correction: suggestion now has its own action; exact response replay,
  partial weights, durable effects, referral attribution, JCS, lease fencing,
  state/expiry/cache/migration behavior, and shared fixtures are selected.
- Review status (2026-07-15): final foundation readiness remains rejected.
  Global-only false capabilities, authority/pytest rules, and migration-marker
  ownership are resolved. Phase 0 generic-path and missing sentinel tests,
  exhaustive canonical declarations/fixtures, and legacy weight compatibility
  remain open. Do not start or deploy Phase 1-2 until renewed approval.
- Structural validation: `ck plan validate
  plans/260714-reliable-write-contract-backend/plan.md --strict` passed on
  2026-07-14 with all seven phase files detected and no syntax/structure warnings;
  rerun after the 2026-07-15 readiness corrections.

### Whole-Plan Consistency Sweep

- Files reread: `plan.md` and Phases 0-6.
- Decision deltas checked: UUID transport; all 13 actions including suggestion;
  RFC 8785 typed inputs; lease token fence; exact response snapshots; durable
  effects; state/expiry; dedicated 30-second cache; partial weight results;
  cross-source referral attribution; PostgreSQL guards; compatibility;
  Phase 0 prerequisite redaction; deploy order; shared fixtures; and false defaults.
- Intentional distinctions checked: legacy versus operation-aware behavior;
  admission kill versus ungated lookup/live-owner completion; exact logical JSON
  versus wire bytes; partial item validation versus atomic accepted-item commit;
  application rollback versus guarded unused-install Alembic downgrade.
- Remaining gates are approvals/ownership values listed above. They cannot turn a
  capability on implicitly; production cohort remains none.

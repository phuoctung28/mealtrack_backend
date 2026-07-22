---
phase: 1
title: "Contract and Migration Foundation"
status: pending
priority: P1
dependencies: [0]
effort: "3-5 engineering days"
---

# Phase 1: Contract and Migration Foundation

## Overview

After Phase 0 corrects instruction authority and makes telemetry redaction safe, create
normalized PostgreSQL persistence, pure domain/app contracts, an RFC 8785
fingerprint, durable effects, and UoW repository seams. No production action is
enabled.

## Context Links

- `docs/system-architecture.md`, `docs/cqrs-guide.md`, `docs/standards/db-api.md`
- `src/infra/database/uow_async.py`
- `src/domain/ports/async_unit_of_work_port.py`
- `migrations/versions/20260702000001_add_food_label_metadata_to_meal.py`

## Prerequisite Gate

Phase 0 is a hard dependency. It corrects the PostgreSQL/CQRS authority and lands
sentinel-tested pre-route redaction before this migration, lookup, or API code can
be deployed. A raw resolved lookup path must never reach a log or telemetry sink.

### Readiness Decision — 2026-07-15

**Rejected / do not start.** No reliable-write migration, model, executor,
manifest, lookup API, or operation-aware route may be implemented or deployed
until Phase 0 completes and the corrected canonical-input and legacy-weight
contracts below receive renewed independent approval. The global-only false
capability model, authority/pytest rules, and migration marker ownership are
resolved and do not require redesign.

## Contract

`client_operation_id` is a lowercase hyphenated RFC 4122 UUIDv4. For a
contract-aware write, `Idempotency-Key` and the body/form field are both required
and normalize to the same UUID. Neither field is authentication.

The server computes, never trusts, fingerprint contract `rw-fp-v1`:

```text
sha256(UTF8("rw-fp-v1\n" + action + "\n") || RFC8785(effective_input))
```

`effective_input` is a typed, post-Pydantic-validation envelope containing only
behavior-affecting fields: contract/action, method, route template, normalized
path parameters, typed query arrays, behavior headers, and the action body or
multipart digest. It excludes operation identity, auth, tracing, ignored legacy
calories, and response-only defaults. Per-action fixture metadata declares every
included field, omitted-vs-null/default expansion, ordered-vs-set array, and
sanitization rule; a field not declared is rejected from the fingerprint input.

RFC 8785/JCS is normative, including UTF-16 property ordering and ECMAScript
binary64 number serialization. Strings preserve Unicode code points unless an
action schema explicitly normalizes human text to NFC before JCS. Reject NaN and
infinities before reservation; map `-0` to `0`; represent money/weight/domain
decimals as schema-versioned canonical decimal strings, not host-language float.
UUIDs use lowercase hyphenated form. Datetimes require an offset and normalize
to exactly six fractional digits plus `Z`, preserving microseconds without
rounding/truncation. Scalar query fields reject repeats; repeatable arrays retain
order unless their action declaration marks them set-valued, then sort after
normalization. Media type is lowercase type/subtype with lowercase, sorted
behavioral parameters; multipart boundary is excluded. Multipart scans include
SHA-256 of bytes, normalized media type, URL/crop parameters, sanitized text,
resolved language, and behavior headers; raw bytes/URLs are never persisted.

Shared fixtures live at `tests/fixtures/reliable_write/v1/fingerprint.json` and
`../mobile/test/fixtures/reliable_write/v1/fingerprint.json` and must be byte-for-
byte identical in source control. They cover Unicode normalization/escaping,
UTF-16 key order, integer/binary64/`-0`/Decimal/exponent forms, omitted/null/
default, timezone offsets/microseconds, repeated query rules, media parameters,
path IDs, sanitized text, language/behavior headers, target date/timezone,
URL/crop, multipart bytes/type, and UUID case. Python and Dart tests must produce
the fixture's canonical UTF-8 hex and SHA-256.

The v1 effective-input declarations are fixed as follows; every optional default
is expanded to its validated effective value, explicit null remains null only
where the domain distinguishes it, and unlisted transport metadata is excluded:

| Action | Included typed effective inputs |
|---|---|
| `meal.manual.create` | resolved target date/timezone, meal type/source, NFC dish/emoji, resolved `Accept-Language` used by the durable value-insight effect, and ordered items with nullable USDA `fdc_id`, nullable NFC `name`, normalized quantity/unit, and all custom nutrition fields (protein/carbs/fat/fiber/sugar); legacy client calories excluded |
| `meal.suggestion.create` | suggestion ID, NFC name/description/cuisine/origin/emoji, meal type/date, resolved target timezone/language, top-level protein/carbs/fat, portion multiplier/cook time, ordered ingredients (name/amount/unit/macros including fiber), ordered instructions, normalized image URL SHA-256, provider/source identity and persisted download-location/public-ID digests; legacy client calories excluded |
| `meal.image.create` | file SHA-256, normalized media type, resolved target date/timezone/language, sanitized description, crop/options, and every persisted provider-affecting upload/analyzer option (provider name/model/version, public-ID/location digest, scan mode) |
| `meal.url.create` | URL SHA-256, public-ID/download-location digests, crop metadata/options, resolved target date/timezone/language, sanitized description, provider name/model/version, and validated transport `scan_mode="scanner"` normalized to canonical enum value `scanner` before fingerprinting and command dispatch |
| `meal.food_label.create` | URL SHA-256, public-ID/download-location digests, label-crop URL/public-ID digests and crop metadata/options, resolved target date/timezone/language, sanitized description, provider name/model/version, and scan mode `food_label` |
| `meal.ingredients.update` | lowercase meal UUID path, NFC `dish_name` (including explicit null), `created_at` normalized to six-digit UTC (including explicit null), normalized `meal_type` (including explicit null), resolved language/timezone, and ordered normalized ingredient edits with every persisted field (action, IDs/source identifiers, name, quantity/unit, macros including fiber) |
| `meal.delete` | lowercase meal UUID path only |
| `weight.create` | client ID, canonical Decimal weight, six-digit UTC instant |
| `weight.sync` | ordered items of client ID, canonical Decimal weight, six-digit UTC instant |
| `weight.delete` | lowercase weight-entry UUID path only |
| `onboarding.complete` | verified Firebase UID path digest and effective completion state/version |
| `promo.redeem` | NFC/case-normalized promo-code HMAC only |
| `referral.apply` | NFC/case-normalized referral-code HMAC, normalized integer `discount_applied`, and uppercase ISO currency; provider resolution is execution output, not client input |

Language/timezone/profile defaults are resolved before reservation and included;
changes on a later call therefore conflict rather than silently changing the
response. URL/code/path values appear only in the in-memory canonical input or
as HMAC/SHA-256 digests and are never copied to logs or the operation row.

Uniqueness is `(user_id, action, client_operation_id)`. Stable actions are
`meal.manual.create`, `meal.suggestion.create`, `meal.image.create`, `meal.url.create`,
`meal.food_label.create`, `meal.ingredients.update`, `meal.delete`,
`weight.create`, `weight.sync`, `weight.delete`, `onboarding.complete`,
`promo.redeem`, and `referral.apply`.

## Data Model and Transaction Rules

Create `reliable_write_operations` with UUID primary key, user FK `CASCADE`,
action, client operation UUID, fingerprint, state, lease token/expiry, result
contract/schema/status/entity ID/canonical date, immutable JSONB exact response,
safe terminal error code, retention expiry, scrubbed-at, and timestamps. Add:

- unique constraint on user/action/client operation;
- lookup index on user/action/client operation;
- cleanup index on state/retention expiry;
- checks for state and 64-character lowercase SHA-256; fingerprint may be null
  only after the row enters `expired` during privacy scrubbing.

JSONB is a documented immutable response-snapshot exception under
`docs/standards/db-api.md`; never store request bodies. The v1 snapshot is capped
at 256 KiB, contains the exact logical JSON response and stable safe headers
(excluding the computed `Idempotency-Replayed` marker), and is created before
commit; exceeding the cap rolls back the mutation. Field order,
whitespace, compression, and transport-generated headers are not contractual,
but parsed JSON, status, content type, and allowlisted response headers are.
Default active retention is 30 days. At expiry, scrub response/fingerprint and
retain a seven-day
`expired` tombstone, then delete. Account deletion cascades immediately.

Create `reliable_write_effects` with operation/user FKs `CASCADE`, effect type,
opaque target key, minimal immutable JSONB payload, `pending|processing|sent|
permanent_failure`, attempt/DB-time lease fields, and unique
`(operation_id,effect_type,target_key)`. Required external/domain effects and
repairable projection/cache effects are inserted in the mutation UoW. Consumers
claim with `FOR UPDATE SKIP LOCKED`, pass the effect UUID as downstream
idempotency identity where the provider supports it, and retry with bounded
backoff. Delivery is at-least-once; a provider without idempotency may observe a
repeat after delivery-before-mark crash, but the local effect row is unique and
no mutation repeats. Replay may signal dispatch
of only an already-recorded pending effect; it never inserts an effect or reruns
the mutation. Effect failure after commit cannot change an operation from
committed to failed. Required effects exhaust into `permanent_failure`, page the
owner, and are retained for manual replay/acknowledgement; repairable projection
effects may be rebuilt from the canonical entity but keep the same unique key.

Create dedicated `reliable_write_capabilities`, owned solely by this migration,
with action PK, compiled contract version, `enabled=false`, `ever_enabled=false`,
updated-at, and revision. This table, not the existing feature-flag service/cache,
is the manifest/kill-switch source. It has no cohort/allowlist column: v1 admission
is global per action/environment. Create `reliable_write_migration_markers` with
primary key `migration_revision`, fixed schema checksum, and `installed_at`; the
migration inserts this marker only after all owned objects and false rows validate
in the same transaction. Create `referral_attributions` with unique
`referred_user_id`, source type, normalized code HMAC, nullable internal referral
and affiliate references, and timestamps; Phase 5 specifies its use.

### Executable Reservation and Lease Fence

1. Reservation transaction uses `INSERT ... ON CONFLICT DO NOTHING RETURNING`.
   The insert winner owns a random lease token. A loser reads the row in a new
   transaction: fingerprint mismatch conflicts; committed/permanent/expired are
   terminal; a DB-time-live pending lease returns in-progress.
2. A stale pending row is claimed only by
   `UPDATE ... SET lease_token=:new, lease_expires_at=db_now()+:ttl WHERE id=:id
   AND state='pending' AND fingerprint=:fp AND lease_token=:old AND
   lease_expires_at<=db_now() RETURNING ...`. No returned row means re-read.
3. Long provider/AI work renews with a token/fingerprint/state CAS using DB time.
   Flag disable blocks new reservations/reclaims but an already-live owner may
   renew and finish; disabled stale work is never resumed.
4. Immediately before invoking the domain mutation, the action UoW runs
   `SELECT ... FOR UPDATE` with user/action/operation/fingerprint/token/state and
   `lease_expires_at>db_now()`. Missing/deleted/account-cascaded or changed rows
   abort before the callback. The row lock is held through mutation, effect
   inserts, response snapshot, and finalization; finalization repeats the token/
   state predicate. Thus an expired old worker cannot enter the mutation after a
   new owner claims it.

## Related Code Files

| Action | Path | Purpose |
|---|---|---|
| Create | `src/domain/model/reliable_write/reliable_write_operation.py` | Pure state/value types |
| Create | `src/domain/ports/reliable_write_operation_repository_port.py` | Async repository contract |
| Create | `src/app/services/reliable_write/fingerprint.py` | Canonicalization + SHA-256 |
| Create | `src/app/services/reliable_write/executor.py` | Reserve/claim/replay/finalize policy |
| Create | `src/infra/database/models/reliable_write_operation.py` | SQLAlchemy model |
| Create | `src/infra/database/models/reliable_write_effect.py` | Durable effect/outbox model |
| Create | `src/infra/database/models/reliable_write_capability.py` | Dedicated kill switch model |
| Create | `src/infra/database/models/reliable_write_migration_marker.py` | Revision ownership/checksum marker |
| Create | `src/infra/database/models/referral/referral_attribution.py` | User-unique internal/affiliate claim |
| Create | `src/infra/repositories/reliable_write_operation_repository_async.py` | Lock/CAS/persist adapter |
| Create | `src/infra/repositories/reliable_write_effect_repository_async.py` | Effect claim/finalize adapter |
| Create | `src/infra/repositories/reliable_write_capability_repository_async.py` | Manifest/admin adapter |
| Modify | `src/infra/repositories/referral_repository.py` | Attribution claim operations |
| Modify | `src/domain/ports/async_unit_of_work_port.py` | Typed operation repository port |
| Modify | `src/infra/database/uow_async.py` | Instantiate repository per fresh UoW |
| Modify | `src/infra/database/models/__init__.py` | Register model for Alembic |
| Create | `migrations/versions/20260714000001_add_reliable_write_contract.py` | PostgreSQL expand schema + false capabilities |
| Create | `tests/migrations/test_reliable_write_operations_migration.py` | `@pytest.mark.postgres` upgrade/downgrade/schema/marker-retry tests |
| Create | `tests/unit/app/services/reliable_write/test_fingerprint.py` | Canonical fixtures |
| Create | `tests/unit/app/services/reliable_write/test_executor.py` | State/concurrency policy |
| Create | `tests/integration/infra/repositories/test_reliable_write_operation_repository_async.py` | DB locks/constraints |
| Modify | `tests/unit/infra/database/test_model_registry_metadata.py` | Registry assertion |

## Implementation Steps

1. Complete the instruction/redaction prerequisite gates. Before service code,
   write byte-identical Python/Dart RFC 8785 fixtures that prove every declared
   input changes the fingerprint, including manual `fdc_id`/`name`/
   `Accept-Language`, suggestion top-level macros, and URL `scanner` mode.
2. Add domain types and repository port. Keep SQLAlchemy/FastAPI imports out.
3. Add ORM model and import it through the central registry.
4. Generate a PostgreSQL migration from the rechecked head. It creates all owned
   tables/checks/indexes and exactly the registry actions as false capability rows,
   then atomically inserts marker revision `20260714000001` with a fixed schema
   checksum. On retry, a matching marker plus exact expected schema/false rows is
   a no-op; a missing marker with any owned object, checksum mismatch, or unexpected
   capability data aborts. It never adopts or overwrites preexisting data. Do not
   backfill legacy writes.
5. Downgrade acquires the same transaction-scoped PostgreSQL advisory lock,
   verifies this revision's marker/checksum, and aborts if any capability has
   `ever_enabled=true` or if any operation, effect, or attribution row exists.
   Only a provably unused install drops owned rows/tables. Application rollback
   is otherwise forward-only.
6. Implement the exact insert/loser/CAS/`FOR UPDATE` fence above plus finalization,
   expiry scrub, and delete. Repository flushes; UoW alone commits.
7. Implement executor policy. It accepts the action UoW for domain+result
   atomicity and never invokes one handler from another.
8. Add architecture tests banning API/infra imports from new domain/app code and
   manual `commit()` in the new repository/service.
9. Decorate every real-PostgreSQL migration/repository test with the registered
   strict `@pytest.mark.postgres`; keep non-database contract tests unmarked.

## Test Scenario Matrix

| Scenario | Expected |
|---|---|
| Same user/action/key/fingerprint | One owner; later call replays |
| Same key, different body | 409 conflict; callback not called |
| Same key, different action/user | Independent operation |
| Crash after reservation | Pending then stale-lease recovery |
| Lease expires during AI; new owner claims | Old token cannot enter mutation; one mutation |
| Account deleted while provider runs | Fence sees no row; no mutation/effect |
| Crash inside action transaction | Mutation and result both rollback |
| Crash after mutation/effect flush before commit | Mutation/result/effects all rollback |
| Expiry | Descriptor scrub -> tombstone -> delete |

## Verification Commands

```bash
uv run pytest tests/unit/app/services/reliable_write tests/integration/infra/repositories/test_reliable_write_operation_repository_async.py -o addopts=""
uv run pytest tests/migrations/test_reliable_write_operations_migration.py tests/migrations/test_alembic_revision_graph.py -m postgres
uv run alembic heads
uv run alembic upgrade head
uv run alembic downgrade 20260702000001
uv run alembic upgrade head
```

## Success Criteria

- [ ] Python and Dart fixtures enumerate every included action field, including
  referral discount/currency; manual item `fdc_id`/`name` and resolved
  `Accept-Language`; suggestion top-level protein/carbs/fat; all meal edit fields;
  URL `scanner` normalization; and every scan/suggestion persisted and
  provider-affecting field, with a changed-field conflict case for each.
- [ ] Concurrent duplicates cannot both execute the mutation callback.
- [ ] Domain mutation, exact response, and required effect rows share one UoW.
- [ ] Real PostgreSQL tests cover first upgrade, interrupted/retry behavior,
  marker/checksum/object collision aborts, guarded downgrade, schema/indexes/checks,
  data-present abort, and one Alembic head.
- [ ] Every seeded action capability is false and `ever_enabled=false`.

## Risks and Security

Reservation and action transactions create a recoverable pending window by
design. Lease claims use DB time and compare-and-swap, not process clocks.
Operation IDs and hashes are high-cardinality private metadata: never log or use
as metric labels. Exact response snapshots are private user data, exist only for
replay/reconciliation, are size/retention bounded, and inherit user-row deletion.

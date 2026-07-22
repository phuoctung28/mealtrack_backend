---
phase: 4
title: "Weight Write Integration"
status: pending
priority: P1
dependencies: [0, 1, 2]
effort: "4-6 engineering days"
---

# Phase 4: Weight Write Integration

## Overview

Give single create, batch sync, and delete stable operation identity and exact
per-item reconciliation. Preserve legacy response fields and keep flags off
until the product gate on single-write timestamp semantics is approved.

## Current Flow and Gap

- Routes: `src/api/routes/v1/weight_entries.py`.
- Commands/handlers: add, sync, delete under `src/app/commands/weight/` and
  `src/app/handlers/command_handlers/`.
- Repository/model: `weight_repository_async.py`, `WeightEntryORM` with unique
  `(user_id, recorded_at)`.
- Migration origin: `057_add_weight_entries_table.py`; timezone correction:
  `20260503113601_fix_datetime_timezone_columns_batch.py`.
- Current single add generates a UUID and plain-inserts; batch generates UUIDs,
  upserts by timestamp, and returns only count/message. Current handlers create
  concrete UoWs and call `commit()` manually. There is no focused weight handler,
  repository-upsert, route-contract, or batch-outcome suite.

## Selected Versioned Weight Contract

New optional request fields remain ignored by legacy clients:

- single item schema adds optional `client_id`/`client_operation_id`, but both
  `client_id: UUID4` and operation ID are required when the header is present;
- sync item: required `client_id: UUID4` when top-level operation is present;
- sync request: top-level `client_operation_id`;
- delete: body `client_operation_id` is required only for operation-aware delete
  (retain path ID and accept an optional JSON body); header must match.

Preserve single response `id`, `weight_kg`, `recorded_at`, `created_at`, message.
Add `client_id`, `server_id`, `canonical_weight_kg`,
`canonical_recorded_at`, and `outcome`. Preserve batch `synced_count` and message;
add ordered `results`:

```json
{"client_id":"...","server_id":"...","canonical_weight_kg":"72.400",
 "canonical_recorded_at":"2026-07-14T08:09:10.123456Z",
 "outcome":"created|updated|duplicate|rejected","error_code":null}
```

V1 selects **partial item acceptance with one atomic persistence transaction for
all accepted items**. Envelope/structural failures (invalid operation/header,
invalid UUID/datetime JSON type, over 100 items, repeated `client_id`, or repeated
canonical instant) return terminal 422 and write nothing. After structural
parsing, each item is independently domain-validated in input order. Invalid
weight/range or policy time returns `rejected`, `server_id=null`, both canonical
fields null, and exactly one allowlisted code
`WEIGHT_OUT_OF_RANGE|RECORDED_AT_OUT_OF_RANGE`; it creates no row. Accepted
items return `created|updated|duplicate` with non-null server/canonical fields.
Unexpected DB failure rolls back every accepted item and the operation remains
retryable; it is never converted into item rejection.

The HTTP status for any structurally valid batch is 200, including all-rejected.
`synced_count` is the count of `created+updated+duplicate`, not input count;
`rejected_count` is explicit; `results` has exactly one row per input in the same
order. The frozen operation response/lookup stores all outcomes and counts, and
replay returns them unchanged. Response message is a stable fixture-derived v1
string, not an input-dependent free-form error.

Require timezone-aware input and normalize to UTC as exactly
`YYYY-MM-DDTHH:MM:SS.ffffffZ`. Preserve microseconds with no rounding or
truncation; offset-equivalent instants collide. Database/session precision must
round-trip six digits. Canonical weight is a versioned fixed-scale decimal
string returned from the persisted NUMERIC row, never a binary float or echoed
before DB validation.

## PostgreSQL NUMERIC Expand Migration

Before reliable weight admission, add a migration chained from the rechecked
Alembic head that creates nullable, unbounded `weight_kg_numeric NUMERIC` beside
legacy `weight_kg FLOAT`, not an in-place type change. Unbounded NUMERIC is
required so the expand migration does not reject current accepted positive
floats above 999.999 kg or below 0.001 kg. Map it in `WeightEntryORM` as
`Numeric(asdecimal=True)` and map the operation-aware domain boundary with
`Decimal`.

Legacy behavior remains authoritative while capabilities are false: legacy
requests keep accepting every value the current `float > 0` schema/storage path
accepts and retain their existing response semantics. Legacy writes always write
the FLOAT column and also write the exact finite `Decimal(str(weight_kg))` to
NUMERIC when representable; a legacy value that cannot be represented in NUMERIC
leaves the nullable column null and is reported by a count-only migration audit,
never rejected or coerced. Backfill applies the same rule to existing rows. Legacy
reads continue using FLOAT, so nullable or higher-precision NUMERIC data cannot
change old-client behavior.

Only operation-aware admission applies the v1 finite 0.001..999.999 kg domain
range and `ROUND_HALF_UP` quantization to 0.001 kg; accepted operation-aware
writes dual-write the canonical NUMERIC value and its FLOAT mirror. These checks
remain unreachable while the action capability is false. Reliable reads require
a non-null NUMERIC value and return its fixed three-decimal representation; they
never reinterpret a legacy-only null as operation-aware success.

A later contract migration may constrain scale, make NUMERIC non-null, or retire
FLOAT only after a full audit proves all legacy-only rows are compatible and
legacy request support has an independently approved migration path. Downgrade is
permitted only when no reliable weight operation is committed and every non-null
NUMERIC value round-trips to its FLOAT mirror under the applicable legacy or v1
policy; otherwise it aborts. Real PostgreSQL tests cover positive legacy values
above 999.999 and below 0.001, exact backfill, nullable fallback, legacy and v1
dual-write paths, half-step v1 rounding, downgrade guards, and Decimal round-trip.

## Single-Create Upsert Decision and Enablement Gate

V1 is selected: operation-aware `weight.create` invokes the exact same
same-UTC-instant repository upsert/classification as one-item sync. It returns
`created`, `duplicate`, or `updated` and never plain-inserts into the unique
constraint. Legacy create retains its existing conflict behavior. Product/mobile
approval of this intentional split and its shared fixtures is required before
`weight.create` can turn on; no implementation choice remains open. Batch/delete
also remain false until partial-result and tombstone fixtures pass.

## Repository Algorithm

For each accepted canonical timestamp in a bounded batch (maximum 100), inside a
single UoW that also finalizes the exact response:

1. `INSERT ... ON CONFLICT DO NOTHING RETURNING id`.
2. If inserted, outcome `created`.
3. Otherwise `SELECT ... FOR UPDATE` existing row. Equal value => `duplicate`;
   changed value => update and `updated`.
4. Return the existing/inserted server ID and canonical DB values.

This avoids unreliable `xmax` inspection and classifies concurrent inserts
correctly. The operation snapshot stores the ordered result array in the same
UoW transaction. Single create calls this algorithm once. Delete stores the exact
success ACK and canonical server ID; replay returns it even though the row is
gone. Repository methods flush only and never commit.

## Related Code Files

| Action | Paths |
|---|---|
| Modify schemas | `src/api/schemas/request/weight_entry_requests.py`, `response/weight_entry_responses.py` |
| Modify route | `src/api/routes/v1/weight_entries.py` |
| Modify commands | `src/app/commands/weight/add_weight_entry_command.py`, `sync_weight_entries_command.py`, `delete_weight_entry_command.py` |
| Modify handlers | `src/app/handlers/command_handlers/add_weight_entry_command_handler.py`, `sync_weight_entries_command_handler.py`, `delete_weight_entry_command_handler.py`; inject `AsyncUnitOfWorkPort` |
| Modify domain | `src/domain/model/weight/weight_entry.py`; add typed upsert outcome DTO |
| Modify repository/model | `src/infra/repositories/weight_repository_async.py`, `src/infra/database/models/weight_entry.py`, `src/infra/mappers/weight_entry_mapper.py` |
| Create migration | `migrations/versions/<head>_expand_weight_kg_numeric.py` | Nullable unbounded PostgreSQL `NUMERIC` expand/backfill/dual-write guard; tests are `@pytest.mark.postgres` |
| Existing migrations | `migrations/versions/057_add_weight_entries_table.py`, `migrations/versions/20260503113601_fix_datetime_timezone_columns_batch.py` |
| Modify composition | `src/api/dependencies/event_bus.py` supplies fresh UoWs |
| Create tests | `tests/unit/api/test_reliable_weight_routes.py`, `tests/unit/handlers/command_handlers/test_reliable_weight_handlers.py` |
| Create integration | `tests/integration/infra/repositories/test_weight_repository_reliable_upsert.py`, `tests/integration/api/test_reliable_weight_writes.py` |

## Implementation Steps

1. Pin old request/response snapshots before adding fields.
2. Add and verify the nullable unbounded NUMERIC expand migration and ORM/mapper
   Decimal boundary before reliable route work; pin full positive-float legacy
   compatibility plus v1 conversion/rounding/fallback/downgrade tests.
3. Add two-tier structural/envelope and per-item domain validators, fixed-scale
   Decimal output, exact UTC serializer, batch bounds, and duplicate checks.
4. Refactor handlers to injected UoW ports; no concrete UoW or manual commit.
5. Implement typed repository outcome algorithm and map ordered client IDs.
6. Wrap create/sync/delete mutation + exact response snapshot in the reliable executor.
7. Ensure a batch retry returns the stored full ordered mapping, including
   rejected rows, without validators causing new upserts or mutations.
7. Keep list pagination unchanged; generic operation lookup is authoritative for
   ambiguous writes, while list remains a projection/repair source.

## Test Scenario Matrix

| Scenario | Expected |
|---|---|
| New timestamp | created + new server ID |
| Same instant/offset, same value | duplicate + existing server ID |
| Same instant, changed value | updated + existing server ID |
| Mixed batch | Ordered per-client independent outcomes |
| Valid plus out-of-range items | 200 partial; rejected null IDs; accepted persist atomically |
| All items rejected | 200, synced_count 0, one rejected result per input |
| Duplicate client ID/timestamp in batch | 422; zero writes |
| `+07:00` vs `Z` same microsecond | Same DB key/server ID; no precision loss |
| Legacy float `72.4005` | `72.401` by fixed `ROUND_HALF_UP`; NUMERIC and mirror/read mapping agree |
| Legacy float above `999.999` | Accepted unchanged by legacy path; exact NUMERIC mirror when representable |
| Legacy positive float below `0.001` | Accepted unchanged by legacy path; no v1 range policy leaks into legacy admission |
| NUMERIC downgrade with mismatch or reliable operation | Abort; no precision/data loss |
| Batch retry | Same mapping; zero repository mutations |
| Timeout after commit/restart | Lookup restores mapping |
| Delete replay | Stable success ACK/server ID |
| Cross-user server ID/delete | 404/403-equivalent without disclosure |

## Verification Commands

```bash
uv run pytest tests/unit/api/test_reliable_weight_routes.py tests/unit/handlers/command_handlers/test_reliable_weight_handlers.py
uv run pytest tests/integration/infra/repositories/test_weight_repository_reliable_upsert.py tests/integration/api/test_reliable_weight_writes.py -o addopts="" -m integration
uv run pytest tests/migrations/test_weight_kg_numeric_migration.py -m postgres
```

## Success Criteria

- [ ] Every input maps to exactly one client ID/outcome; accepted rows have
  server/canonical values and rejected rows have null values plus safe code.
- [ ] Single and batch operation-aware upsert semantics match the selected v1
  fixtures; product/mobile approval gates enablement only.
- [ ] Persisted/replayed UTC and Decimal strings match Python/Dart fixtures.
- [ ] Nullable unbounded PostgreSQL NUMERIC expand/backfill/dual-write/downgrade
  behavior preserves all current legacy positive-float writes and the ORM mapping
  passes real-database compatibility tests before weight admission.
- [ ] Legacy request/response snapshots pass unchanged.
- [ ] Retry and lookup return the same ordered mapping.

## Risks and Security

Weight is sensitive health data. Do not log, metric-label, or copy values,
timestamps, IDs, operation keys, or result arrays outside the authenticated
response and private operation row. Telemetry uses action, outcome, count, and
bounded duration only.

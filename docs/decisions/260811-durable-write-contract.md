# Durable Write Contract (Manual Meal Slice)

**Status:** Accepted  
**Date:** 2026-08-11  
**Scope:** Server-side operation identity for mutation replay; Phase 5 vertical slice.

## Context

Mobile must not blind-retry meal mutations after ambiguous transport failures.
Meal-recommendations already use `Idempotency-Key` + fingerprint. Manual meal
create and weight sync still lack operation identity.

## Decision

1. **Header:** `Idempotency-Key` (trimmed, 1–160 chars) on supported mutations.
2. **Identity:** unique `(user_id, action, idempotency_key)`.
3. **Fingerprint:** SHA-256 of canonical JSON for the request body fields that
   define the logical write (sorted keys).
4. **Replay:** same key + same fingerprint → exact prior HTTP status + body.
5. **Conflict:** same key + different fingerprint → `409` with
   `IDEMPOTENCY_KEY_CONFLICT`.
6. **Retention:** 14 days (`expires_at`); expired rows may be pruned.
7. **Discovery:** `GET /v1/capabilities/durable-writes`.
8. **Backward compatibility:** omitting the header keeps legacy single-shot
   behavior (no store write).

### Actions in this wave

| Action | Supported | Notes |
|---|---|---|
| `manual_meal_create` | yes | `POST /v1/meals/manual` |
| `weight_sync` | no | Deferred: no client entry ID → server ID mapping yet |

Automatic client replay stays **off** until mobile fixtures pass and a later
rollout enables it per capability.

## Consequences

- Mobile can send a stable key for manual meal create and treat 409 as a hard
  client bug (key reuse with different payload).
- Weight durable path remains unsupported until mapping ships.
- Edit / suggestion / scan actions reuse this store later behind the same
  capability document.

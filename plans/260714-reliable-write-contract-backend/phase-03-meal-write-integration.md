---
phase: 3
title: "Meal Write Integration"
status: pending
priority: P1
dependencies: [0, 1, 2]
effort: "5-8 engineering days"
---

# Phase 3: Meal Write Integration

## Overview

Integrate reliable writes into every requested meal action while preserving the
legacy no-operation request path. All action flags remain off through this phase.

## Current Flow Inventory

| Route | Command -> handler | Persistence/tests |
|---|---|---|
| `POST /v1/meals/manual` | `CreateManualMealCommand` -> `CreateManualMealCommandHandler` | `AsyncMealRepository`; `test_create_manual_meal_command_handler.py`, `test_meals_api.py`, `test_manual_meal_with_target_date.py` |
| `POST /v1/meal-suggestions/save` | `SaveMealSuggestionCommand` -> `SaveMealSuggestionCommandHandler` | `AsyncMealRepository`; `test_meal_suggestions_routes.py`, `test_meal_suggestion_cqrs_handlers.py` |
| `POST /v1/meals/image/analyze` | `UploadMealImageImmediatelyCommand` -> `UploadMealImageImmediatelyHandler` | Cloudinary + AI + meal UoW; `tests/unit/app/handlers/command_handlers/test_upload_meal_image_immediately_command_handler.py`, `tests/unit/infra/database/test_uow_meal_suggestion_boundary.py` |
| `POST /v1/meals/scan-by-url` | `ScanByUrlCommand` -> `ScanByUrlCommandHandler` | AI + meal UoW; app-smoke, food-guard, beverage-routing tests |
| `POST /v1/meals/food-label/scan-by-url` | same command with `scan_mode=food_label` | same handler/repository/tests |
| `PUT /v1/meals/{meal_id}/ingredients` | `EditMealCommand` -> `EditMealCommandHandler` | `AsyncMealRepository`; edit handler/API tests |
| `DELETE /v1/meals/{meal_id}` | `DeleteMealCommand` -> `DeleteMealCommandHandler` | `src/infra/repositories/meal_repository_async.py` and `src/infra/repositories/hydration_repository_async.py`; `tests/unit/handlers/command_handlers/test_meal_delete_command_handlers.py`, `tests/integration/test_meal_edit_api.py` |

The registry/action for the suggestion row is exactly
`meal.suggestion.create`; it has its own false capability and never aliases
`meal.manual.create`.

## Request and Replay Contract

- JSON requests add optional `client_operation_id: UUID4`; multipart image adds
  an optional form field. Routes also accept `Idempotency-Key`.
- Both absent: exact legacy behavior. One present, invalid, or mismatch: 400.
  Both present while action flag is off: `409 WRITE_CAPABILITY_DISABLED` before
  upload, AI, DB, cache, translation, or background work.
- Exact replay contract `rw-response-v1` is selected: same key/fingerprint
  returns the stored first-call status, content type, echoed key, and
  `application/json` body with parsed-JSON equality. The transport-only
  `Idempotency-Replayed` header is false on first response and true on replay and
  is not part of the frozen snapshot. A replay never rehydrates the
  entity and never adds a fresher translation, insight, timestamp, or detail.
  Wire whitespace/key order/compression/date headers are outside the contract.
- For operation-aware meal writes, the handler constructs an application-owned,
  JSON-compatible frozen DTO from the canonical persisted meal inside the action
  UoW; it does not import API schemas. The API response model is a contract-tested
  mirror and the route returns the frozen body without post-commit requery.
  Optional projections (translation and value insights) are
  deterministically `null`/absent according to the versioned fixture on the
  first response as well as replay; legacy calls retain today's projection
  timing. The serialized, schema-validated body (maximum 256 KiB), status, and
  safe headers finalize in the same transaction. Serialization/cap failure
  rolls back the meal. The API returns only that frozen DTO.
- Shared `rw-response-v1` fixtures pin manual, suggestion, image, URL,
  food-label, edit, and delete first/replay pairs in both repositories. Mobile
  approval of these exact logical JSON fixtures is an enablement gate, not an
  unresolved backend implementation choice.
- Add response headers `Idempotency-Key` and `Idempotency-Replayed: true|false`
  only for operation-aware calls. Existing response fields and status codes stay.
- Required and repairable effects are recorded exactly once in
  `reliable_write_effects` in the mutation UoW. Required: Unsplash download
  tracking and integration/domain-event publication. Repairable projection:
  cache invalidation, translation, and value-insight generation. A committed
  operation is successful even while these effects are pending.

For op-aware multipart upload, derive Cloudinary public ID from a server-secret
HMAC of user/action/operation rather than a random second ID. Never expose or log
the HMAC input. This makes external upload overwrite/retry deterministic while
the meal row remains protected by the operation record. Legacy uploads stay as-is.

## Calories and Canonical Inputs

The operation fingerprint uses effective validated inputs, not ignored client
metadata. Suggestion `calories` remains accepted for old clients but is excluded
from authoritative persistence and fingerprinting. Add optional `fiber` defaults
to suggestion/ingredient schemas; calculate through domain `Macros.calories`:
`P*4 + (C-fiber)*4 + fiber*2 + F*9`. Manual custom nutrition continues using its
existing fiber-aware backend calculation. API response calories come from the
saved domain nutrition only.

## Related Code Files

| Action | Paths |
|---|---|
| Create | `src/api/dependencies/reliable_write.py`, `src/api/schemas/request/reliable_write_requests.py` |
| Create | `src/app/dto/reliable_write_result.py` | Typed frozen v1 HTTP response snapshot |
| Modify routes | `src/api/routes/v1/meals.py`, `meal_scan_by_url.py`, `meal_suggestions.py` |
| Modify schemas | `src/api/schemas/request/meal_requests.py`, `meal_suggestion_requests.py`; response meal/suggestion schemas only for optional operation metadata if mobile needs body access |
| Modify commands | `src/app/commands/meal/create_manual_meal_command.py`, `upload_meal_image_immediately_command.py`, `scan_by_url_command.py`, `edit_meal_command.py`, `delete_meal_command.py`; `src/app/commands/meal_suggestion/save_meal_suggestion_command.py` |
| Modify handlers | `src/app/handlers/command_handlers/create_manual_meal_command_handler.py`, `upload_meal_image_immediately_command_handler.py`, `scan_by_url_command_handler.py`, `edit_meal_command_handler.py`, `delete_meal_command_handler.py`, `meal_suggestion/save_meal_suggestion_command_handler.py` |
| Modify composition | `src/api/dependencies/event_bus.py` |
| Existing repo/model/migration | `src/infra/repositories/meal_repository_async.py`, `src/infra/repositories/hydration_repository_async.py`, `src/infra/database/models/meal/meal.py`, `migrations/versions/20260702000001_add_food_label_metadata_to_meal.py` |
| Create effects | `src/cron/reliable_write_effects.py`, `src/infra/services/reliable_write_effect_dispatch_service.py` |
| New tests | `tests/unit/api/test_reliable_meal_write_routes.py`, `tests/integration/api/test_reliable_meal_writes.py` |
| Extend tests | `tests/integration/api/test_meals_api.py`, `tests/integration/test_manual_meal_with_target_date.py`, `tests/integration/test_meal_edit_api.py`, `tests/unit/api/test_meal_suggestions_routes.py`, `tests/unit/api/test_app_smoke_routes.py`, and listed handler suites |

## Implementation Steps

1. Add red route tests for absent/partial/mismatch/disabled/enabled contracts.
2. Build request contexts at the API boundary after Pydantic validation. Include
   path IDs, query/form fields, language-affecting inputs, and file hash.
3. Add optional reliable context to each command. Action constants stay in code;
   clients cannot choose action.
4. Reserve before Cloudinary/AI on scans and renew long leases. At the mutation
   fence, use one action UoW for meal, effect rows, and exact v1 response. Remove
   explicit handler commits; UoW alone commits.
5. For manual/suggestion/edit/delete, execute mutation, effect insertion, response
   serialization, and finalization under the same UoW. Replay only returns the
   snapshot and offers pending recorded effects to the dispatcher.
6. Store the exact response body because replay requires it; classify it as
   private user data with user-cascade, retention scrub, 256 KiB check, no logs,
   and no analytics/Sentry attachment. Never store request/AI payloads.
7. Preserve existing response schemas/statuses. Operation-aware v1 may only add
   the documented headers; its deterministic null projection fields are pinned.
8. Implement idempotent effect consumers. Each consumer uses the effect UUID as
   its downstream idempotency key where supported, marks success in a separate
   UoW, and can repair after process crash. Provider calls are never made while
   holding the operation DB lock. Cache/projection/provider failure after commit
   cannot produce a mutation 5xx or change the frozen response.
9. Replace touched logs containing raw user/meal/image/body data with action,
   outcome, replay boolean, bounded latency, and error class.

## Test Scenario Matrix

| Scenario | Expected |
|---|---|
| Duplicate manual/suggestion create | Same frozen body; one meal/effect set |
| Timeout after meal commit | Lookup committed; replay returns same entity |
| Same operation, changed target date/item | 409; original unchanged |
| Duplicate scan while first pending | No second AI/upload; pending response |
| Scan crash after upload | Deterministic asset reuse; no duplicate meal |
| Crash after commit before effect dispatch | Replay/cron repairs pending effects; no mutation rerun |
| Effect delivery succeeds then mark crashes | One local effect; retry uses provider key or documented at-least-once delivery |
| Replayed edit | Original frozen response; edit count increments once |
| Replayed/already-missing delete | Same success ACK; no repeated events |
| Fiber present | Calories use backend fiber-aware formula |
| Legacy request | Existing snapshots/status/body unchanged |

## Verification Commands

```bash
uv run pytest tests/unit/api/test_reliable_meal_write_routes.py tests/unit/handlers/command_handlers/test_create_manual_meal_command_handler.py tests/unit/app/handlers/command_handlers/test_upload_meal_image_immediately_command_handler.py tests/unit/api/test_meal_suggestions_routes.py tests/unit/api/test_app_smoke_routes.py
uv run pytest tests/integration/api/test_reliable_meal_writes.py -o addopts="" -m integration
uv run pytest tests/unit/handlers/command_handlers/test_meal_edit_command_handlers.py tests/unit/handlers/command_handlers/test_meal_delete_command_handlers.py
```

## Success Criteria

- [ ] Every listed meal action has disabled, first-call, duplicate, conflict,
  pending, timeout-after-commit, and owner-isolation coverage.
- [ ] Scan external work cannot run twice for a live identical operation.
- [ ] First/replay parsed JSON and status match shared `rw-response-v1` fixtures;
  no entity rehydration occurs.
- [ ] Faults at every effect insert/commit/dispatch/mark boundary are recoverable.
- [ ] Legacy route responses remain compatible.
- [ ] All persisted/displayed calories derive from saved macros.

## Risks and Security

Scans span non-transactional providers. Durable reservation plus deterministic
asset identity bounds duplicate side effects; the DB still owns canonical meal
identity. The bounded private response snapshot necessarily contains existing
response fields, but raw food/image/user-description data must not appear in
operation metadata, effect keys, logs, metrics, traces, Sentry, or analytics.

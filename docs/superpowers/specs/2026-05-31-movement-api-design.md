# Movement API Design

Date: 2026-05-31

## Goal

Implement the Movement feature from `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/docs/movement-api.md`.

The backend will support manual movement logging, daily movement retrieval, deletion, and calorie balance integration. Movement calories are active calories supplied by the mobile client; the backend persists them and uses only entries with `include_in_balance = true` to adjust calorie balance.

## API Surface

Base path: `/v1/movement`

Endpoints:

- `POST /log`: create a manual movement entry for the authenticated user.
- `GET /daily?date=YYYY-MM-DD`: return entries for one local date, newest first, plus daily active calorie goal.
- `DELETE /{entry_id}`: permanently delete an entry owned by the authenticated user.

The route will follow existing FastAPI/CQRS patterns:

- API layer parses dates, reads `X-Timezone`, obtains authenticated `user_id`, and sends commands/queries through the configured event bus.
- Application handlers perform validation and persistence through `AsyncUnitOfWork`.
- Infrastructure repository owns SQLAlchemy queries.
- Domain model remains dependency-free.

## Data Model

Add a dedicated `movement_entries` table instead of storing movement as meals or generic activities.

Columns:

- `id`: string primary key, `mvmt_` prefixed generated ID.
- `user_id`: foreign key to `users.id`, indexed.
- `activity_name`: string, 1-100 chars, stored as sent by the client.
- `duration_min`: integer, 1-600.
- `kcal_burned`: float, active calories, non-negative.
- `intensity`: string enum values `light`, `moderate`, `hard`.
- `source`: string enum values `manual`, `apple_health`; `POST /log` always uses `manual`.
- `include_in_balance`: boolean, default true.
- `logged_at`: timezone-aware UTC datetime used for local-date queries.
- `created_at` and `updated_at`: standard timestamps from `BaseMixin`.

Indexes:

- `idx_movement_entries_user_logged_at` on `(user_id, logged_at)`.
- `idx_movement_entries_user_id` on `user_id`.

Daily filtering will use a UTC range derived from the user's local date and timezone instead of `DATE(logged_at)`, keeping the query index-friendly.

## Timezone Rules

The request date is a user-local date.

- If `target_date` or query `date` is omitted, handlers use today's date in the resolved user timezone.
- If `target_date` is provided, the created entry's `logged_at` is local noon converted to UTC for that date. This matches the existing date-safe pattern used for manual date logging and prevents UTC boundary drift.
- Daily retrieval converts the requested local date into `[local midnight, next local midnight)` in UTC.
- The user timezone is resolved through `resolve_user_timezone_async`, using stored user timezone first and `X-Timezone` as fallback.

Dates more than one day in the future are rejected with `INVALID_DATE`.

## Application Components

New domain files:

- `src/domain/model/movement/movement_entry.py`
- `src/domain/model/movement/movement_enums.py`

New application files:

- `src/app/commands/movement/log_movement_command.py`
- `src/app/commands/movement/delete_movement_entry_command.py`
- `src/app/queries/movement/get_daily_movement_query.py`
- `src/app/handlers/command_handlers/log_movement_command_handler.py`
- `src/app/handlers/command_handlers/delete_movement_entry_command_handler.py`
- `src/app/handlers/query_handlers/get_daily_movement_query_handler.py`

New API/schema files:

- `src/api/routes/v1/movement.py`
- `src/api/schemas/request/movement_requests.py`

New infrastructure files:

- `src/infra/database/models/movement_entry.py`
- `src/infra/mappers/movement_entry_mapper.py`
- `src/infra/repositories/movement_repository_async.py`
- Alembic migration for `movement_entries`.

Registration updates:

- Include movement router in `src/api/main.py`.
- Import movement handlers in command/query handler package initializers.
- Attach `uow.movement_entries` in `AsyncUnitOfWork`.
- Import the ORM model in `src/infra/database/models/__init__.py`.

## Validation And Errors

Validation will use explicit `MealTrackException` subclasses or `ValidationException` with API-contract error codes.

Rules:

- Missing required fields rely on FastAPI/Pydantic 422 behavior.
- `duration_min` outside 1-600 returns `INVALID_DURATION`.
- `kcal_burned < 0` returns `INVALID_KCAL`.
- `intensity` outside `light`, `moderate`, `hard` returns `INVALID_INTENSITY`.
- Malformed or too-far-future date returns `INVALID_DATE`.
- Delete of a missing or non-owned entry returns `ENTRY_NOT_FOUND`.

The public contract lists `FORBIDDEN` for deleting another user's entry. The repository will use owner-scoped delete and return `ENTRY_NOT_FOUND` for non-owned IDs, avoiding an ownership oracle. This is safer and consistent with many existing owner-scoped repository methods. If exact `403` semantics are required later, the repository can add an unscoped existence check.

## Response Shape

Movement entry responses:

```json
{
  "id": "mvmt_...",
  "activity_name": "Badminton",
  "duration_min": 60,
  "kcal_burned": 231.0,
  "intensity": "moderate",
  "source": "manual",
  "include_in_balance": true,
  "logged_at": "2026-05-31T05:00:00+00:00"
}
```

Daily summary response:

```json
{
  "date": "2026-05-31",
  "goal_kcal": 300.0,
  "entries": []
}
```

`goal_kcal` will default to `300.0`. Goal persistence endpoints are out of scope for v1.

## Calorie Balance Integration

Movement affects calorie balance only when `include_in_balance = true`.

Daily nutrition summary changes:

- Fetch included movement kcal for the requested local date.
- Keep macro totals unchanged.
- Compute `net_calories = food_calories - included_movement_kcal`.
- Return `total_calories = net_calories` from `GetDailyMacrosQueryHandler`, because `MealMapper.to_daily_nutrition_response` maps this value to public `consumed_calories` and derives `remaining_calories` from it.
- Add internal handler fields `food_calories` and `movement_kcal_burned` so tests and future response mapping can distinguish food intake from movement adjustment without changing macro totals.
- Use `net_calories` for weekly context daily consumed input.
- Clamp public `remaining_calories` through the existing mapper behavior; do not clamp `net_calories` before mapping, because a negative net value accurately means activity exceeded intake.

Bulk nutrition changes:

- Fetch included movement kcal for the requested date range.
- Set `totals.consumed.calories` to per-date `net_calories`.
- Add sibling fields to each date summary: `food_calories` and `movement_kcal_burned`.
- Apply the same per-date `net_calories = consumed_food_calories - included_movement_kcal` adjustment in `totals.remaining.calories`.
- Preserve macro consumed/target/remaining calculations.

The integration will invalidate daily macros, bulk nutrition, and activities-style caches for affected dates when movement entries are logged or deleted.

## Activities Integration

The movement API owns movement retrieval. Existing `/v1/activities/daily` currently reserves workout activities for future use, but this implementation will not add movement entries to `/v1/activities`. The required contract is `/v1/movement/daily`; activities integration can be designed separately if the mobile app later needs a unified timeline.

## Testing

Use TDD for implementation.

Initial failing tests:

- `POST /v1/movement/log` persists a manual entry and returns the contract response.
- Invalid duration, kcal, intensity, and malformed/future dates return the expected codes.
- `GET /v1/movement/daily` returns only entries for the requested user-local date, newest first, with `goal_kcal = 300.0`.
- `DELETE /v1/movement/{entry_id}` deletes only owner-scoped entries and returns `204`.
- Daily nutrition calorie remaining includes movement balance adjustment without changing macro totals.
- Bulk nutrition applies movement adjustment per date.
- Date filtering respects `X-Timezone` around UTC boundaries.

Focused verification:

- Run movement API/unit tests first.
- Run daily/bulk nutrition handler tests.
- Run affected route smoke tests.

## Out Of Scope

- Apple Health bulk import endpoint.
- Weekly movement endpoint.
- Movement goal persistence endpoints.
- Server-side MET calorie recalculation.
- Mobile catalog validation.

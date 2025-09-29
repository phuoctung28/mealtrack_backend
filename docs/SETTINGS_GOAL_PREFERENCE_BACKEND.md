## Feature: Settings Goal Preference — Backend Support

### Overview
Add a dedicated endpoint for updating a user’s fitness goal from Settings. The endpoint updates the user’s current profile `fitness_goal`, recalculates TDEE/macros, and returns the updated calculation to the client. This enables the mobile “Goal” preference to persist changes end-to-end.

### API
- Method: `PATCH`
- Path: `/v1/user-profiles/{user_id}/goal`
- Request:
```json
{
  "goal": "maintenance | cutting | bulking"
}
```
- Response: `TdeeCalculationResponse`
```json
{
  "bmr": 1675.2,
  "tdee": 2365.8,
  "macros": { "calories": 2366, "protein": 160, "carbs": 280, "fat": 80 },
  "goal": "cutting",
  "activity_multiplier": 1.55,
  "formula_used": "mifflin_st_jeor"
}
```
- Errors:
  - 400: Invalid goal value
  - 404: User or current profile not found
  - 500: Server error

### Functional Requirements
- Update only the `fitness_goal` field on the current `UserProfile` row.
- Leave other profile attributes unchanged.
- Immediately compute and return new TDEE/macros using the same pipeline as `/v1/user-profiles/{user_id}/tdee`.
- Ensure mapping aligns with domain enums: maintenance, cutting, bulking.
- Log structured event for observability: `user_goal_updated` with `{ user_id, previous_goal, new_goal }`.

### Non-Functional Requirements
- p95 latency < 800ms on warm DB (re-using existing query path for TDEE).
- Idempotent: PATCHing same goal returns success and the same TDEE/macros.
- Safe concurrency: serializes on DB transaction for profile update.
- Minimal PII in logs; no sensitive data values.

### Data Model
- Table: `user_profiles`
  - `fitness_goal` (string): one of maintenance|cutting|bulking
  - `is_current` (bool): select row with `is_current = true`

### Implementation Plan
1) Request DTO: `UpdateFitnessGoalRequest { goal: GoalEnum }`.
2) Route: `@router.patch("/v1/user-profiles/{user_id}/goal")` → validate request, send command, then query TDEE and return `TdeeCalculationResponse`.
3) Command: `UpdateUserGoalCommand(user_id, goal)`; Handler loads current profile and updates `fitness_goal` using `UserRepository.update_user_goals(...)`.
4) Reuse `GetUserTdeeQueryHandler` to compute macros.
5) Add structured logs and basic error handling.

### Acceptance Criteria
- AC-1: PATCH with `goal=bulking` updates profile and returns TDEE/macros with `goal="bulking"`.
- AC-2: PATCH with same current goal returns 200 with current TDEE/macros.
- AC-3: PATCH invalid goal returns 400.
- AC-4: PATCH unknown user returns 404.

### Risks & Mitigations
- Enum mismatch: centralize goal mapping; add unit test for mapping.
- Stale caches: mobile will refresh macros via response; no server cache to invalidate.

### Telemetry
- Log `user_goal_updated` (info) and `user_goal_update_failed` (warning) with minimal identifiers and error code.

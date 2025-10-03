## MVP Spec (Backend): Metrics Update → Daily Nutrition Recalculation

### Context
Mobile MVP supports manual updates to weight, activity level, and optional body fat %. The app recalculates daily calories/macros client-side immediately. Backend must persist metrics, expose current daily targets for consistency, and be ready to compute/validate targets server-side if needed.

### Goals
- Persist profile metrics updates with minimal friction.
- Provide a simple way to fetch daily nutrition targets (authoritative or mirrored).
- Keep the design small and shippable; defer devices/offline/history to later.

### Out of Scope (MVP)
- Device integrations, event-driven nudges, audit/history, offline queues, complex feature flags beyond existing infra.

## Functional Requirements

1) Update Metrics
- Accept updates for: `weightKg` (or `weightLb`), `activityLevel` (enum), `bodyFatPercent` (optional).
- Validate ranges (weight > 0; activity level in enum; body fat 0–70% hard, warn if 5–60% not enforced at API).
- Persist to user profile with `updated_at` timestamps per field.
- Return the latest profile and a `daily_targets` object. For MVP, the `daily_targets` can be:
  - Echo of client computation (if provided by client), OR
  - Computed server-side using current rules (preferred if trivial to reuse existing goal engine), OR
  - Omitted if compute not ready (client remains source of truth). Choose one path and keep consistent.

2) Get Daily Targets
- Provide a read endpoint to fetch current daily targets for a user for a given date (defaults to today).
- If server compute exists, calculate using latest profile + goal settings; otherwise return last saved targets snapshot (if client posted it), or 404/empty if none.

3) Consistency
- A metrics update should make the subsequent `GET daily-targets` reflect the new profile immediately (either computed now or using the posted snapshot).

## API (Proposed)

- POST `/api/v1/users/{user_id}/metrics`
  - Auth: required
  - Body (any subset):
    ```json
    {
      "weightKg": 72.3,
      "activityLevel": "moderately_active",
      "bodyFatPercent": 18.5,
      "dailyTargetsSnapshot": {
        "calories": 2200,
        "proteinGrams": 140,
        "carbsGrams": 240,
        "fatGrams": 73
      }
    }
    ```
  - Response 200:
    ```json
    {
      "profile": { "weightKg": 72.3, "activityLevel": "moderately_active", "bodyFatPercent": 18.5 },
      "dailyTargets": { "calories": 2200, "proteinGrams": 140, "carbsGrams": 240, "fatGrams": 73 }
    }
    ```

- GET `/api/v1/users/{user_id}/daily-targets?date=YYYY-MM-DD`
  - Auth: required
  - Response 200:
    ```json
    { "date": "2025-09-29", "dailyTargets": { "calories": 2200, "proteinGrams": 140, "carbsGrams": 240, "fatGrams": 73 } }
    ```
  - 404 if targets unavailable and server compute disabled.

Notes:
- If a server compute path is available, omit `dailyTargetsSnapshot` from POST; compute on the backend for stronger consistency.

## Data & Validation

Profile fields (user table or profile table):
- `weight_kg` DECIMAL NULL
- `activity_level` ENUM('sedentary','lightly_active','moderately_active','very_active','extra_active')
- `body_fat_percent` DECIMAL NULL
- `updated_at` per field (or a single `profile_updated_at` with field-level audit later)

Targets snapshot (optional MVP table):
- `user_id`, `date`, `calories`, `protein_g`, `carbs_g`, `fat_g`, `computed_source` ENUM('client','server'), `computed_at`
- Unique (user_id, date)

## Non-Functional (MVP)
- Latency: P95 ≤ 300ms for POST metrics (DB write + optional compute) and GET targets.
- AuthN/Z: require user auth; scope access to own resources.
- Observability: minimal request logging and error metrics; no PII in logs.
- Stability: strict validation; graceful 4xx on bad input; predictable 5xx on internal errors.

## Minimal Server Compute (if enabled)
- Inputs: user profile (sex, age, height from existing records), latest `weight_kg`, `activity_level`, optional `body_fat_percent`, and current goal settings.
- Use Katch–McArdle when body fat present; else Mifflin–St Jeor + activity multiplier.
- Apply current product goal adjustments and macro split.
- Save daily snapshot and return in responses.

## Acceptance Criteria
- POST metrics updates profile fields and returns 200 with updated profile and daily targets (server-computed or snapshot echoed), within P95 ≤ 300ms.
- GET daily-targets returns values consistent with the latest metrics change for today.
- Invalid payloads (bad enum, negative weight, body fat > 70) return 400 with a concise message.
- Auth required; cross-user access denied (403/404).

## Rollout
- Feature-flag server compute; default to client snapshot echo if compute flag off.
- Add simple dashboard panel in ops to monitor request count, error rate, P95 latency.



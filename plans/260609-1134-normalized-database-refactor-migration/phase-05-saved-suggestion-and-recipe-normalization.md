---
phase: 5
title: "Saved suggestion and recipe normalization"
status: completed
priority: P1
effort: "1-2 weeks"
dependencies: [1, 2]
---

# Phase 5: Saved suggestion and recipe normalization

## Context Links

- Model: `src/infra/database/models/saved_suggestion.py`
- Repositories: `src/infra/repositories/saved_suggestion_db_repository_async.py`, `src/infra/repositories/saved_suggestion_db_repository.py`
- Routes: `src/api/routes/v1/saved_suggestions.py`
- Meal model: `src/infra/database/models/meal/meal.py`

## Overview

Normalize saved suggestion and recipe instruction payloads so queryable meal/recipe data is not trapped in JSON.

## Key Insights

- `saved_suggestions.suggestion_data` is opaque JSON.
- `meal.instructions` is JSON list data on a broad meal table.
- API currently accepts/returns `suggestion_data`, so compatibility lives in repository/mapper layer.

## Requirements

- Functional: saved-suggestion API remains compatible.
- Functional: new normalized rows support ingredients/steps/macros without parsing JSON.
- Non-functional: malformed legacy suggestion JSON does not break list endpoint.

## Architecture

Keep `saved_suggestions` as header table. Add child tables:

- `saved_suggestion_items(saved_suggestion_id, name, quantity, unit, protein_g, carbs_g, fat_g, fiber_g, sugar_g, calories, position)`
- `saved_suggestion_steps(saved_suggestion_id, instruction, duration_minutes, position)`
- optional explicit header fields on `saved_suggestions`: `dish_name`, `description`, `calories`, `protein_g`, `carbs_g`, `fat_g`, `fiber_g`, `sugar_g`, `language`.

For meal recipes, add:

- `meal_instruction_steps(meal_id, instruction, duration_minutes, position)`

Keep legacy JSON columns until phase 7.

## Related Code Files

| Action | File |
|---|---|
| Modify | `src/infra/database/models/saved_suggestion.py` |
| Create | `src/infra/database/models/saved_suggestion_item.py` |
| Create | `src/infra/database/models/saved_suggestion_step.py` |
| Create | `src/infra/database/models/meal/meal_instruction_step.py` |
| Modify | `src/infra/database/models/__init__.py` |
| Modify | `src/infra/repositories/saved_suggestion_db_repository_async.py` |
| Modify | `src/infra/repositories/saved_suggestion_db_repository.py` |
| Modify | `src/api/routes/v1/saved_suggestions.py` only if request validation needs stronger shape |
| Modify | `src/api/mappers/meal_suggestion_mapper.py` if used for saved payload projection |
| Create | `migrations/versions/YYYYMMDDHHMMSS_normalize_saved_suggestions_and_recipe_steps.py` |
| Add | `tests/integration/infra/repositories/test_saved_suggestion_repository_async.py` |
| Add/Modify | `tests/unit/handlers/query_handlers/test_cached_query_handlers.py` |

## Implementation Steps

1. Use canonical `users.id` for `saved_suggestions.user_id`; audit and repair any legacy Firebase UID/outlier rows before adding FK.
2. Tests before: list/save/delete saved suggestion with existing JSON shape and cache invalidation.
3. Add normalized child tables with cascades from `saved_suggestions.id`.
4. Backfill child rows from `suggestion_data`, tolerating missing fields and preserving raw JSON.
5. Update save path to populate normalized children and legacy `suggestion_data`.
6. Update read path to project response from normalized rows first; fallback to legacy JSON if children are missing.
7. Add `meal_instruction_steps` and dual-write from meal suggestion save/manual recipe paths where `Meal.instructions` is set.
8. Do not drop `suggestion_data` or `meal.instructions` yet.

## Test Scenario Matrix

| Scenario | Test |
|---|---|
| Legacy JSON saved suggestion lists unchanged | query handler test |
| New save dual-writes header/items/steps + JSON | repository integration |
| Malformed legacy payload does not 500 | repository test |
| Cache invalidated after save/delete | cached handler test |
| Recipe instructions read normalized first | mapper/repository test |
| FK add waits for legacy outlier audit/repair | migration precondition |

## Success Criteria

- [x] Saved suggestions can be queried without JSON parsing for core fields.
- [x] Existing API request/response shapes still work.
- [x] Recipe steps have stable child rows with ordering.
- [x] Legacy JSON remains only compatibility/raw snapshot.

## Risk Assessment

High data-shape risk because AI-generated suggestion JSON may vary. Mitigation: tolerant parser, raw snapshot retention, and fallback reads.

## Security Considerations

Saved suggestions are private user data. Do not expose raw malformed payloads in errors/logs.

## Next Steps

Normalize food catalog details, notification context ownership, and payout details.

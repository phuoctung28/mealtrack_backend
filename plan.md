# Discovery-to-Recipe Reliability Plan

## Summary

`POST /v1/meal-suggestions/discover` and `POST /v1/meal-suggestions/recipes` are linked, but the current backend loses discovery context. Discovery returns meal names and macro estimates, then `/recipes` only receives names plus an optional broad calorie target. Recipe generation recalculates from generated ingredients and may reject recipes when deterministic calories do not fit the target scale window.

The fix is to persist discovery candidates with the session, then make `/recipes` hydrate selected discovery meals into detailed recipes without rejecting them for calorie scaling. The backend should return one detailed recipe per selected discovery meal, preserving order and using backend-derived calories.

## Key Changes

- Persist discovery candidates with the suggestion session for the existing 4-hour TTL.
- Add stable `disc_...` ids to discovery meals before the session is saved.
- Add a preferred `/recipes` payload using `session_id` plus `selected_meal_ids`.
- Keep the existing `meal_names` and `calorie_target` payload as a backward-compatible fallback.
- Use each selected discovery meal's calorie estimate as that recipe's calorie target.
- Add a selected-recipe generation path that preserves input order and returns one recipe per selected meal.
- Do not reject selected recipes due to calorie scale factor. Always scale ingredient quantities toward the selected discovery target when deterministic calories are positive.
- Repair incomplete AI output by retrying or filling missing recipe steps instead of dropping a selected meal.

## Test Plan

- Discovery returns meal ids, English names, and macro calories.
- Discovery candidates are persisted with the session.
- `/recipes` with `session_id` and 3 selected ids returns exactly 3 recipes.
- Returned recipe order matches `selected_meal_ids`.
- A low-calorie selected meal with raw deterministic calories above target is scaled and returned, not rejected.
- Missing `recipe_steps` is repaired or filled with fallback steps.
- Existing `meal_names` plus `calorie_target` request remains supported.
- Calories remain backend-derived from macros.

## Assumptions

- Mobile will call `/recipes` after `/discover` using `session_id` plus selected discovery meal ids.
- The endpoint remains synchronous.
- For selected meals, the backend should prefer a usable adjusted recipe over rejecting for calorie mismatch.

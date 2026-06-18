---
type: brainstorm
title: Workout calorie credit in weekly budget
status: approved
created: "2026-06-18T01:08:00+07:00"
branch: feat/workout-calorie-credit-weekly-budget
---

# Workout Calorie Credit in Weekly Budget

## Summary

Users expect logged workouts to add calories back to their balance. Daily and bulk nutrition already use `food_calories - movement_kcal_burned`, but weekly redistribution uses meal calories only. Fix weekly adjusted targets so `include_in_balance = true` movement credits reduce calorie consumption for weekly budget math.

## Decision

Use net weekly calories: `net_consumed_calories = food_calories - included_movement_kcal`. Keep consumed protein/carbs/fat as food-only macro grams.

## Scope

- Backend only.
- No schema migration.
- No response-shape change.
- No expected-movement/TDEE offset.
- Full logged workout calorie credit when `include_in_balance = true`.

## Acceptance Examples

- Weekly target 14000, base 2000/day, Monday food 2300, Monday workout 200, Tuesday adjustment: `(14000 - 2100) / 6 = 1983.3` before macro fitting/caps.
- Weekly target 14000, Monday food 2500, Monday workout 500, Tuesday adjustment: `(14000 - 2000) / 6 = 2000`.

## Science Note

This is correct under Nutree's selected definition: base target excludes logged workouts, so workout calories are additional expenditure. If the base TDEE already included those workouts, full credit would double count.

## Risks

- Weekly `consumed_calories` becomes net calories, matching daily/bulk but possibly surprising clients that expected food-only calories.
- Negative net consumption is possible when movement exceeds food; keep it, because it accurately represents calorie balance.

# Fitness Goal System

Unified system for health metrics and goal-based calculations.

## Goal Enums

Unified 3-value structure used across all layers:
- **CUT**: Caloric deficit (-500 kcal), high protein.
- **BULK**: Caloric surplus (+300 kcal), high carbs.
- **RECOMP**: Maintenance (0 kcal), balanced macros.

## TDEE Calculation

Calculated using the Mifflin-St Jeor formula, adjusted by non-exercise job/lifestyle activity and the chosen Fitness Goal.

Planned training volume is not added to baseline TDEE. Workout calories are credited only when users log movement entries with `include_in_balance = true`; this prevents double-counting the same exercise in both TDEE and logged movement.

## Multi-Layer Mapping

- **API Layer**: lowercase `cut`, `bulk`, `recomp`.
- **Domain Layer**: uppercase `CUT`, `BULK`, `RECOMP`.
- **Database Layer**: lowercase strings stored in `user_metrics` table.

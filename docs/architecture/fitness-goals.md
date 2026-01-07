# Fitness Goal System

Unified system for health metrics and goal-based calculations.

## Goal Enums

Unified 3-value structure used across all layers:
- **CUT**: Caloric deficit (-500 kcal), high protein.
- **BULK**: Caloric surplus (+300 kcal), high carbs.
- **RECOMP**: Maintenance (0 kcal), balanced macros.

## TDEE Calculation

Calculated using the Mifflin-St Jeor formula, adjusted by Activity Level and the chosen Fitness Goal.

## Multi-Layer Mapping

- **API Layer**: lowercase `cut`, `bulk`, `recomp`.
- **Domain Layer**: uppercase `CUT`, `BULK`, `RECOMP`.
- **Database Layer**: lowercase strings stored in `user_metrics` table.

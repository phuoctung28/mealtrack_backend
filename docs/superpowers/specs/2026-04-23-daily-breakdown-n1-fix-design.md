# Fix N+1 Query in Daily Breakdown Endpoint

**Date**: 2026-04-23  
**Status**: Approved  
**Endpoint**: `/v1/meals/weekly/daily-breakdown`

## Problem

The daily breakdown endpoint experiences unnecessary database overhead due to SQLAlchemy's `lazy="joined"` configuration on the `MealORM.image` relationship. Even when using the `MACROS_ONLY` projection (which only needs nutrition data), the query includes a `LEFT OUTER JOIN mealimage`, fetching image metadata for every meal.

**Observed SQL:**
```sql
SELECT meal.*, mealimage_1.*
FROM meal
LEFT OUTER JOIN mealimage AS mealimage_1 ON mealimage_1.image_id = meal.image_id
WHERE meal.created_at >= ... AND meal.user_id = ... AND meal.status != ...
```

**Impact**: 41 events observed, affecting 9 users over 30 days.

## Solution

Add `noload(MealORM.image)` to the `MACROS_ONLY` projection options. This explicitly instructs SQLAlchemy to skip the image relationship for this projection, eliminating the unnecessary JOIN.

## Changes

### Files Modified

| File | Change |
|------|--------|
| `src/infra/repositories/meal_repository.py` | Add `noload` import, update `MACROS_ONLY` projection |
| `src/infra/repositories/meal_repository_async.py` | Add `noload` import, update `MACROS_ONLY` projection |

### Code Change

```python
from sqlalchemy.orm import noload, selectinload, joinedload

_PROJECTION_OPTS: dict = {
    MealProjection.MACROS_ONLY: (
        noload(MealORM.image),
        selectinload(MealORM.nutrition).selectinload(NutritionORM.food_items),
    ),
    MealProjection.FULL: (
        joinedload(MealORM.image),
        selectinload(MealORM.nutrition).selectinload(NutritionORM.food_items),
    ),
    MealProjection.FULL_WITH_TRANSLATIONS: (
        joinedload(MealORM.image),
        selectinload(MealORM.nutrition).selectinload(NutritionORM.food_items),
        joinedload(MealORM.translations),
    ),
}
```

### Expected SQL After Fix

```sql
SELECT meal.meal_id, meal.user_id, meal.status, meal.created_at, ...
FROM meal
WHERE meal.created_at >= ... AND meal.user_id = ... AND meal.status != ...
```

No JOIN to mealimage.

## Safety

- The `GetDailyBreakdownQueryHandler` does not access `meal.image` — it only reads `meal.status`, `meal.created_at`, and `meal.nutrition.macros`
- Meals returned with `MACROS_ONLY` projection will have `image = None`, which is expected behavior
- Other projections (`FULL`, `FULL_WITH_TRANSLATIONS`) are unchanged

## Testing

1. Run existing tests to verify no regressions
2. Manually call `/v1/meals/weekly/daily-breakdown` and verify response is correct
3. Check SQL logs to confirm no mealimage JOIN

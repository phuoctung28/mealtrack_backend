# Daily Breakdown N+1 Query Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate unnecessary mealimage JOIN in the daily-breakdown endpoint by adding `noload()` to MACROS_ONLY projection.

**Architecture:** Add explicit `noload(MealORM.image)` to the `_PROJECTION_OPTS[MACROS_ONLY]` tuple in both sync and async meal repositories. This prevents SQLAlchemy from JOINing the mealimage table when only macro nutrition data is needed.

**Tech Stack:** SQLAlchemy 2.0 async, Python 3.11+

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/infra/repositories/meal_repository.py` | Modify | Sync repository - add noload import and update MACROS_ONLY |
| `src/infra/repositories/meal_repository_async.py` | Modify | Async repository - add noload import and update MACROS_ONLY |

---

### Task 1: Update Async Repository

**Files:**
- Modify: `src/infra/repositories/meal_repository_async.py:8,43-46`

- [ ] **Step 1: Add noload import**

In `src/infra/repositories/meal_repository_async.py`, update line 8:

```python
from sqlalchemy.orm import selectinload, joinedload, noload
```

- [ ] **Step 2: Update MACROS_ONLY projection**

Update lines 43-46 to add `noload(MealORM.image)`:

```python
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

- [ ] **Step 3: Verify syntax**

Run: `python -m py_compile src/infra/repositories/meal_repository_async.py`
Expected: No output (success)

---

### Task 2: Update Sync Repository

**Files:**
- Modify: `src/infra/repositories/meal_repository.py:7,41-54`

- [ ] **Step 1: Add noload import**

In `src/infra/repositories/meal_repository.py`, update line 7:

```python
from sqlalchemy.orm import Session, joinedload, selectinload, noload
```

- [ ] **Step 2: Update MACROS_ONLY projection**

Update lines 41-54 to add `noload(MealORM.image)`:

```python
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

- [ ] **Step 3: Verify syntax**

Run: `python -m py_compile src/infra/repositories/meal_repository.py`
Expected: No output (success)

---

### Task 3: Run Tests and Commit

- [ ] **Step 1: Run repository tests**

Run: `pytest tests/ -k "meal" --tb=short -q`
Expected: All tests pass

- [ ] **Step 2: Run type check**

Run: `mypy src/infra/repositories/meal_repository.py src/infra/repositories/meal_repository_async.py --ignore-missing-imports`
Expected: No errors

- [ ] **Step 3: Commit the fix**

```bash
git add src/infra/repositories/meal_repository.py src/infra/repositories/meal_repository_async.py
git commit -m "perf: add noload(image) to MACROS_ONLY projection

Prevents unnecessary LEFT JOIN to mealimage table in daily-breakdown
endpoint, reducing query overhead for /v1/meals/weekly/daily-breakdown.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4: Manual Verification

- [ ] **Step 1: Start dev server**

Run: `uvicorn src.api.main:app --reload`

- [ ] **Step 2: Call endpoint and check logs**

Call the endpoint with SQL logging enabled to verify no mealimage JOIN:

```bash
curl -H "Authorization: Bearer <token>" \
     -H "X-Timezone: America/Los_Angeles" \
     "http://localhost:8000/v1/meals/weekly/daily-breakdown"
```

Expected: Response returns successfully, SQL logs show no `LEFT OUTER JOIN mealimage`

# P0 Quick Wins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all P0 recommendations from the 2026-04-24 performance audit design doc.

**Architecture:** Remove unused endpoints and dead code, adjust pool timeout for fail-fast behavior, add cache observability logging.

**Tech Stack:** FastAPI, SQLAlchemy, Redis, Python 3.11+

---

## File Structure

### Files to Delete
```
src/api/routes/v1/daily_meals.py
src/api/schemas/request/daily_meal_requests.py
src/api/schemas/response/daily_meal_responses.py
src/api/mappers/daily_meal_mapper.py
src/app/commands/daily_meal/
src/app/queries/daily_meal/
src/app/events/daily_meal/
src/app/handlers/command_handlers/generate_daily_meal_suggestions_command_handler.py
src/app/handlers/command_handlers/generate_single_meal_command_handler.py
src/domain/services/daily_meal_suggestion_service.py
tests/unit/api/test_daily_meal_mapper.py
```

### Files to Modify
```
src/api/routes/v1/meal_suggestions.py     # Remove GET /image endpoint
src/api/main.py                            # Remove commented daily_meals import
src/api/dependencies/event_bus.py          # Remove daily_meal registrations
src/api/schemas/response/__init__.py       # Remove daily_meal exports
src/api/schemas/request/__init__.py        # Remove daily_meal exports
src/api/mappers/__init__.py                # Remove DailyMealMapper export
src/app/commands/__init__.py               # Remove daily_meal exports
src/app/queries/__init__.py                # Remove daily_meal exports
src/app/events/__init__.py                 # Remove daily_meal exports
src/infra/database/config.py               # Change POOL_TIMEOUT default 30→10
src/domain/services/meal_suggestion/nutrition_lookup_service.py  # Add cache logging
```

---

## Task 1: Remove GET /meal-suggestions/image Endpoint

**Files:**
- Modify: `src/api/routes/v1/meal_suggestions.py:389-414`

**Why:** This endpoint is not called by the mobile app. Image fetching is done inline in `/discover`.

- [ ] **Step 1: Run tests to establish baseline**

```bash
pytest tests/unit/api/ -v --tb=short -q 2>&1 | tail -20
```

Expected: All tests pass (or note existing failures)

- [ ] **Step 2: Remove the get_food_image endpoint**

Delete lines 389-414 from `src/api/routes/v1/meal_suggestions.py`:

```python
# DELETE THIS ENTIRE BLOCK (lines 389-414):

@router.get("/image", response_model=FoodImageResponse)
@limiter.limit("30/minute")
async def get_food_image(
    request: Request,
    q: str = Query(
        ..., min_length=2, max_length=100, description="English food search query"
    ),
    _user_id: str = Depends(get_current_user_id),
):
    """Search for a food image by query. Returns 200 with image data or 204 if not found."""
    try:
        from src.api.dependencies.food_image import get_food_image_service

        image_service = get_food_image_service()
        result = await image_service.search_food_image(q)
        if result is None:
            return Response(status_code=204)
        return FoodImageResponse(
            url=result.url,
            thumbnail_url=result.thumbnail_url,
            source=result.source,
            photographer=result.photographer,
        )
    except Exception as e:
        logger.warning(f"Food image search failed for query '{q}': {e}")
        return Response(status_code=204)
```

- [ ] **Step 3: Remove unused import if orphaned**

Check if `FoodImageResponse` is still used elsewhere in the file. If only used by the deleted endpoint, remove from imports at top of file:

```python
# Check line ~29-35 for this import, remove if orphaned:
from src.api.schemas.response.meal_suggestion_responses import (
    ...
    FoodImageResponse,  # Remove this line if orphaned
    ...
)
```

- [ ] **Step 4: Run tests to verify no regressions**

```bash
pytest tests/unit/api/ -v --tb=short -q
```

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add src/api/routes/v1/meal_suggestions.py
git commit -m "refactor: remove unused GET /meal-suggestions/image endpoint

Endpoint not called by mobile app. Image fetching is done inline in /discover.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Reduce Pool Timeout to 10s

**Files:**
- Modify: `src/infra/database/config.py:94`

**Why:** Fail fast under load instead of waiting 30s for a connection.

- [ ] **Step 1: Locate the POOL_TIMEOUT default**

Open `src/infra/database/config.py` and find line 94:

```python
POOL_TIMEOUT = int(os.getenv("POOL_TIMEOUT", "30"))
```

- [ ] **Step 2: Change default from 30 to 10**

```python
POOL_TIMEOUT = int(os.getenv("POOL_TIMEOUT", "10"))
```

- [ ] **Step 3: Run database-related tests**

```bash
pytest tests/unit/infra/ -v --tb=short -q 2>&1 | tail -20
```

Expected: All tests pass (pool timeout is runtime config, not tested directly)

- [ ] **Step 4: Commit**

```bash
git add src/infra/database/config.py
git commit -m "perf: reduce pool_timeout from 30s to 10s for fail-fast behavior

Under load, waiting 30s for a connection leads to request pile-up.
10s timeout fails faster, allowing load balancer to retry elsewhere.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Remove daily_meals Dead Code

**Files:**
- Delete: Multiple files (see File Structure above)
- Modify: Multiple `__init__.py` files to remove exports

**Why:** Router is already commented out in main.py. Remove all orphaned code.

### Step 3.1: Remove event_bus registrations

- [ ] **Step 1: Open event_bus.py and locate daily_meal imports**

File: `src/api/dependencies/event_bus.py`

Remove these import blocks:

```python
# Lines ~7-8: Remove these imports
from src.app.commands.daily_meal import (
    GenerateDailyMealSuggestionsCommand,
    ...
)

# Lines ~57: Remove handler import
GenerateDailyMealSuggestionsCommandHandler,

# Lines ~135+: Remove query imports
from src.app.queries.daily_meal import (
    ...
)

# Lines ~415-416: Remove handler registration
GenerateDailyMealSuggestionsCommand,
GenerateDailyMealSuggestionsCommandHandler(),
```

- [ ] **Step 2: Run tests after removing registrations**

```bash
pytest tests/unit/api/ -v --tb=short -q
```

Expected: Pass (no tests depend on daily_meal handlers)

- [ ] **Step 3: Commit**

```bash
git add src/api/dependencies/event_bus.py
git commit -m "refactor: remove daily_meal handler registrations from event_bus

Daily meals router is disabled. Remove dead handler registrations.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

### Step 3.2: Remove schema exports

- [ ] **Step 4: Remove from response/__init__.py**

File: `src/api/schemas/response/__init__.py`

Remove lines:
```python
from .daily_meal_responses import (
    DailyMealSuggestionsResponse,
    ...
)

# And from __all__:
'DailyMealSuggestionsResponse',
```

- [ ] **Step 5: Remove from request/__init__.py**

File: `src/api/schemas/request/__init__.py`

Remove lines:
```python
from .daily_meal_requests import (
    ...
)
```

- [ ] **Step 6: Remove from mappers/__init__.py**

File: `src/api/mappers/__init__.py`

Remove lines:
```python
from .daily_meal_mapper import DailyMealMapper

# And from __all__:
'DailyMealMapper',
```

- [ ] **Step 7: Remove from commands/__init__.py**

File: `src/app/commands/__init__.py`

Remove lines:
```python
from .daily_meal import (
    GenerateDailyMealSuggestionsCommand,
    ...
)

# And from __all__:
"GenerateDailyMealSuggestionsCommand",
```

- [ ] **Step 8: Remove from queries/__init__.py**

File: `src/app/queries/__init__.py`

Remove lines:
```python
from .daily_meal import (
    ...
)
```

- [ ] **Step 9: Remove from events/__init__.py**

File: `src/app/events/__init__.py`

Remove lines:
```python
from .daily_meal import (
    DailyMealsGeneratedEvent,
    ...
)

# And from __all__:
"DailyMealsGeneratedEvent",
```

- [ ] **Step 10: Commit schema/export cleanup**

```bash
git add src/api/schemas/ src/api/mappers/__init__.py src/app/commands/__init__.py src/app/queries/__init__.py src/app/events/__init__.py
git commit -m "refactor: remove daily_meal exports from __init__.py files

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

### Step 3.3: Delete dead files

- [ ] **Step 11: Delete route file**

```bash
rm src/api/routes/v1/daily_meals.py
```

- [ ] **Step 12: Delete schema files**

```bash
rm src/api/schemas/request/daily_meal_requests.py
rm src/api/schemas/response/daily_meal_responses.py
```

- [ ] **Step 13: Delete mapper file**

```bash
rm src/api/mappers/daily_meal_mapper.py
```

- [ ] **Step 14: Delete command directory**

```bash
rm -rf src/app/commands/daily_meal/
```

- [ ] **Step 15: Delete query directory**

```bash
rm -rf src/app/queries/daily_meal/
```

- [ ] **Step 16: Delete events directory**

```bash
rm -rf src/app/events/daily_meal/
```

- [ ] **Step 17: Delete handler files**

```bash
rm src/app/handlers/command_handlers/generate_daily_meal_suggestions_command_handler.py
rm src/app/handlers/command_handlers/generate_single_meal_command_handler.py
```

- [ ] **Step 18: Delete domain service**

```bash
rm src/domain/services/daily_meal_suggestion_service.py
```

- [ ] **Step 19: Delete test file**

```bash
rm tests/unit/api/test_daily_meal_mapper.py
```

- [ ] **Step 20: Remove commented import from main.py**

File: `src/api/main.py`

Remove line ~237:
```python
# app.include_router(daily_meals_router)
```

And remove the import at the top if present:
```python
# from src.api.routes.v1.daily_meals import router as daily_meals_router
```

- [ ] **Step 21: Run full test suite**

```bash
pytest tests/ -v --tb=short -q 2>&1 | tail -30
```

Expected: All tests pass (daily_meal tests deleted, no other dependencies)

- [ ] **Step 22: Commit file deletions**

```bash
git add -A
git commit -m "refactor: delete daily_meals dead code

Removed:
- src/api/routes/v1/daily_meals.py
- src/api/schemas/*/daily_meal_*.py
- src/api/mappers/daily_meal_mapper.py
- src/app/commands/daily_meal/
- src/app/queries/daily_meal/
- src/app/events/daily_meal/
- src/app/handlers/command_handlers/generate_*_meal_*_handler.py
- src/domain/services/daily_meal_suggestion_service.py
- tests/unit/api/test_daily_meal_mapper.py

Router was already disabled in main.py. This removes all orphaned code.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Add Cache Hit Rate Logging

**Files:**
- Modify: `src/domain/services/meal_suggestion/nutrition_lookup_service.py`

**Why:** We don't know our current cache hit rate. Need visibility to track optimization impact.

- [ ] **Step 1: Add cache metrics tracking to NutritionLookupService**

Add a metrics counter at class level in `nutrition_lookup_service.py` after the logger definition (~line 26):

```python
logger = logging.getLogger(__name__)

# Cache metrics for observability
_cache_metrics = {
    "redis_hits": 0,
    "redis_misses": 0,
    "t1_hits": 0,
    "t2_hits": 0,
    "t3_hits": 0,
}
```

- [ ] **Step 2: Update _lookup_ingredient to track metrics**

In the `_lookup_ingredient` method (~line 137), add metric tracking after each resolution:

```python
async def _lookup_ingredient(
    self, name: str, quantity_g: float
) -> IngredientMacros:
    """Resolve macros for one ingredient: Redis → T1 → T2 → T3."""
    normalized = normalize_food_name(name)
    cache_key = f"nutrition:{normalized}"

    # Check Redis cache first
    if self._redis:
        try:
            cached = await self._redis.get(cache_key)
            if cached:
                _cache_metrics["redis_hits"] += 1
                data = json.loads(cached)
                return self._build_from_cached(data, name, quantity_g)
        except Exception as exc:
            logger.warning("Redis get failed for %s: %s", cache_key, exc)
    
    _cache_metrics["redis_misses"] += 1

    # T1: exact match on name_normalized
    ref = self._repo.find_by_normalized_name(normalized)
    if ref:
        _cache_metrics["t1_hits"] += 1
        result = self._calculate_from_ref(
            ref, name, quantity_g, "T1_food_reference"
        )
        await self._cache_result(cache_key, result)
        return result

    # T2: FatSecret (resolver handles caching to food_reference)
    try:
        per100 = await asyncio.wait_for(
            self._resolver.resolve(name), timeout=T2_TIMEOUT
        )
    except asyncio.TimeoutError:
        logger.warning("T2 FatSecret timeout for %s", name)
        per100 = None
    if per100 is not None:
        _cache_metrics["t2_hits"] += 1
        result = self._build_from_per100(per100, name, quantity_g, "T2_fatsecret")
        await self._cache_result(cache_key, result)
        return result

    # T3: AI estimate — last resort
    _cache_metrics["t3_hits"] += 1
    try:
        result = await asyncio.wait_for(
            self._ai_estimate(name, quantity_g), timeout=T3_TIMEOUT
        )
        await self._cache_result(cache_key, result)
        return result
    except asyncio.TimeoutError:
        logger.warning("T3 AI timeout for %s", name)
        return IngredientMacros(
            name=name,
            quantity_g=round(quantity_g, 1),
            calories=0.0,
            protein=0.0,
            carbs=0.0,
            fat=0.0,
            fiber=0.0,
            sugar=0.0,
            source_tier="T3_ai_estimate",
        )
```

- [ ] **Step 3: Add method to retrieve and log metrics**

Add after the `_aggregate` method (~line 461):

```python
@staticmethod
def get_cache_metrics() -> dict:
    """Return current cache metrics for monitoring."""
    total = _cache_metrics["redis_hits"] + _cache_metrics["redis_misses"]
    hit_rate = (
        _cache_metrics["redis_hits"] / total * 100 if total > 0 else 0.0
    )
    return {
        **_cache_metrics,
        "total_lookups": total,
        "redis_hit_rate_pct": round(hit_rate, 1),
    }

@staticmethod
def log_cache_metrics() -> None:
    """Log current cache metrics at INFO level."""
    metrics = NutritionLookupService.get_cache_metrics()
    logger.info(
        "[NUTRITION-CACHE] hits=%d misses=%d hit_rate=%.1f%% | "
        "T1=%d T2=%d T3=%d",
        metrics["redis_hits"],
        metrics["redis_misses"],
        metrics["redis_hit_rate_pct"],
        metrics["t1_hits"],
        metrics["t2_hits"],
        metrics["t3_hits"],
    )
```

- [ ] **Step 4: Add periodic logging in calculate_meal_macros**

Modify `calculate_meal_macros` to log metrics every 100 calls:

```python
async def calculate_meal_macros(
    self, ingredients: List[Dict[str, Any]]
) -> MealMacros:
    """Calculate deterministic macros for a list of ingredients."""
    tasks = [
        self._lookup_ingredient(
            ing["name"],
            self._to_grams(ing["name"], float(ing["amount"]), ing["unit"]),
        )
        for ing in ingredients
    ]
    results: List[IngredientMacros] = await asyncio.gather(*tasks)
    
    # Log cache metrics every 100 lookups
    total = _cache_metrics["redis_hits"] + _cache_metrics["redis_misses"]
    if total > 0 and total % 100 == 0:
        self.log_cache_metrics()
    
    return self._aggregate(list(results))
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/unit/domain/services/ -v --tb=short -q 2>&1 | tail -20
```

Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/domain/services/meal_suggestion/nutrition_lookup_service.py
git commit -m "feat: add cache hit rate logging to NutritionLookupService

Tracks Redis hits/misses and T1/T2/T3 resolution counts.
Logs metrics every 100 lookups for observability.
Adds get_cache_metrics() for programmatic access.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Verification

- [ ] **Final: Run full test suite**

```bash
pytest tests/ -v --tb=short 2>&1 | tail -50
```

Expected: All tests pass

- [ ] **Final: Run linting**

```bash
black src/ tests/ --check && flake8 src/ --max-line-length=100
```

Expected: No issues (or run `black src/ tests/` to fix)

- [ ] **Final: Verify app starts**

```bash
timeout 10 uvicorn src.api.main:app --host 0.0.0.0 --port 8000 || true
```

Expected: App starts without import errors

---

## Summary

| Task | Files Changed | Estimated Time |
|------|---------------|----------------|
| 1. Remove GET /image | 1 file | 15 min |
| 2. Pool timeout | 1 file | 10 min |
| 3. Remove daily_meals | 15+ files deleted | 45 min |
| 4. Cache logging | 1 file | 30 min |
| **Total** | | **~1.5 hours** |

# Meal Suggestion Performance Optimization Design

## Summary

Optimize `/discover` and `/recipes` endpoints to meet latency targets:
- `/discover`: ≤3s (currently 4-8s)
- `/recipes`: ≤5s (currently 6-12s)

**Approach:** Cache-first strategy with parallelization — eliminate unnecessary work, parallelize I/O, fail fast with graceful degradation.

## Context

The current two-step flow is:
1. `/discover` — lightweight meal grid (names + macros + images)
2. `/recipes` — full recipes for user-selected meals

This replaces the all-in-one `/generate` endpoint which created 3 full recipes upfront.

### Current Bottlenecks

**`/discover`:**
- Image search is sequential (6 awaits in a loop)
- Cache lookup calls Gemini API for embeddings on hot path
- Meal image cache guarded by feature flag (unnecessary complexity)
- ANN queries are sequential (6 DB calls)

**`/recipes`:**
- Recipe timeout is 35s per recipe (too generous)
- Nutrition lookup is sequential per ingredient
- T2/T3 fallbacks can block indefinitely

## Design

### 1. `/discover` Optimizations

#### 1.1 Parallelize image search for cache misses

**File:** `src/api/routes/v1/meal_suggestions.py` (lines 170-187)

```python
# BEFORE: Sequential
for i, m in enumerate(meals):
    if cache_hits[i] is not None:
        images_list.append(cache_hits[i])
        continue
    img_result = await image_service.search_food_image(m["english_name"])

# AFTER: Parallel
miss_indices = [i for i, hit in enumerate(cache_hits) if hit is None]
miss_names = [meals[i]["english_name"] for i in miss_indices]

async def safe_fetch(name: str) -> Optional[FoodImageResult]:
    try:
        return await asyncio.wait_for(
            image_service.search_food_image(name),
            timeout=3.0
        )
    except Exception:
        return None

miss_results = await asyncio.gather(*[safe_fetch(n) for n in miss_names])
```

#### 1.2 Batch ANN query in cache service

**File:** `src/domain/services/meal_image_cache/meal_image_cache_service.py`

Add `query_nearest_batch()` to execute a single pgvector query for all embeddings instead of N sequential calls.

#### 1.3 Remove meal image cache feature flag

Remove `MEAL_IMAGE_CACHE_ENABLED` flag entirely — cache is always enabled.

**Files:**
- `src/infra/config/settings.py` — delete `MEAL_IMAGE_CACHE_ENABLED` field
- `src/api/routes/v1/meal_suggestions.py` — remove `if cfg.MEAL_IMAGE_CACHE_ENABLED:` conditional, always use cache

### 2. `/recipes` Optimizations

#### 2.1 Tighten timeouts + early-stop

**File:** `src/domain/services/meal_suggestion/recipe_attempt_builder.py`

```python
PARALLEL_SINGLE_MEAL_TIMEOUT = 20  # was 35
```

**File:** `src/domain/services/meal_suggestion/parallel_recipe_generator.py`

```python
MIN_ACCEPTABLE_RESULTS = 1  # was 2 — allow partial results
```

#### 2.2 Batch T1 nutrition lookup

**File:** `src/domain/services/meal_suggestion/nutrition_lookup_service.py`

```python
# Add batch method to food reference repository
async def find_batch_by_normalized_names(self, names: list[str]) -> dict[str, FoodRef]:
    # SELECT * FROM food_reference WHERE name_normalized IN (:names)
    ...
```

#### 2.3 Redis cache for nutrition data

**File:** `src/domain/services/meal_suggestion/nutrition_lookup_service.py`

```python
NUTRITION_CACHE_TTL = 86400  # 24 hours

async def _lookup_ingredient(self, name: str, quantity_g: float) -> IngredientMacros:
    key = f"nutrition:{normalize_food_name(name)}"
    
    # Check Redis first
    cached = await self._redis.get(key)
    if cached:
        return self._build_from_cached(json.loads(cached), name, quantity_g)
    
    # T1 → T2 → T3 fallback chain
    result = await self._lookup_chain(name, quantity_g)
    
    # Cache for next time
    await self._redis.setex(key, NUTRITION_CACHE_TTL, json.dumps(result.to_cache_dict()))
    return result
```

#### 2.4 Cap T2/T3 fallback time

```python
T2_TIMEOUT = 2.0  # FatSecret
T3_TIMEOUT = 3.0  # AI estimate
```

### 3. Caching Strategy

| Cache | Storage | TTL | Purpose |
|-------|---------|-----|---------|
| Nutrition | Redis | 24 hours | Skip DB + API calls for repeated ingredients |
| Meal images | Postgres (pgvector) | Permanent | Skip image search |
| Image search | In-memory LRU | 7 days | Already exists |

### 4. Error Handling & Fallbacks

#### Image search fallbacks
- Cache lookup fails → Skip cache, proceed to image search
- Image search times out (3s) → Return null, mobile shows emoji
- All images fail → Return meals without images

#### Recipe generation fallbacks
- Recipe timeout (20s) → Try alternate model pool
- Both models fail for 1 recipe → Return partial results
- All recipes fail → Return error with retry suggestion

#### Nutrition lookup fallbacks
- Redis unavailable → Skip cache, hit DB directly
- T1 miss → T2 (FatSecret)
- T2 timeout (2s) → T3 (AI estimate)
- T3 timeout (3s) → Category-based estimate

```python
CATEGORY_ESTIMATES = {
    "protein": {"protein": 25, "carbs": 0, "fat": 5},
    "grain": {"protein": 3, "carbs": 25, "fat": 1},
    "vegetable": {"protein": 2, "carbs": 5, "fat": 0},
    "default": {"protein": 5, "carbs": 10, "fat": 5},
}
```

### 5. Testing

#### Unit tests
- `tests/unit/api/test_discover_parallel_images.py` — parallel fetch verification
- `tests/unit/domain/services/test_meal_image_cache_batch.py` — batch ANN query
- `tests/unit/domain/services/test_nutrition_lookup_batch.py` — batch T1 lookup
- `tests/unit/domain/services/test_nutrition_redis_cache.py` — Redis cache hit/miss
- `tests/unit/domain/services/test_recipe_timeout.py` — 20s timeout + early-stop
- `tests/unit/api/test_discover_fallbacks.py` — partial failure handling

#### Integration tests
- `tests/integration/api/test_discover_latency.py` — verify <3s with warm cache
- `tests/integration/api/test_recipes_latency.py` — verify <5s

## Files to Modify

| File | Changes |
|------|---------|
| `src/api/routes/v1/meal_suggestions.py` | Parallelize image fetch, remove cache flag conditional |
| `src/domain/services/meal_image_cache/meal_image_cache_service.py` | Add batch ANN query |
| `src/domain/ports/vector_cache_port.py` | Add `query_nearest_batch()` interface |
| `src/infra/repositories/vector_cache_repository.py` | Implement batch query |
| `src/infra/config/settings.py` | Remove `MEAL_IMAGE_CACHE_ENABLED` flag |
| `src/domain/services/meal_suggestion/recipe_attempt_builder.py` | Reduce timeout to 20s |
| `src/domain/services/meal_suggestion/parallel_recipe_generator.py` | Early-stop at 1 success |
| `src/domain/services/meal_suggestion/nutrition_lookup_service.py` | Add Redis cache + batch lookup |
| `src/domain/ports/meal_suggestion_repository_port.py` | Add batch nutrition lookup interface |
| `src/infra/repositories/food_reference_repository.py` | Implement batch query |

## New Files

| File | Purpose |
|------|---------|
| `tests/unit/api/test_discover_parallel_images.py` | Parallel image fetch tests |
| `tests/unit/domain/services/test_nutrition_redis_cache.py` | Redis cache tests |
| `tests/integration/api/test_discover_latency.py` | Latency regression tests |
| `tests/integration/api/test_recipes_latency.py` | Latency regression tests |

## Expected Outcomes

| Endpoint | Current | Target | Mechanism |
|----------|---------|--------|-----------|
| `/discover` (cold) | 4-8s | ≤3s | Parallel image fetch |
| `/discover` (warm) | 3-5s | ≤1.5s | Cache hits + parallel |
| `/recipes` | 6-12s | ≤5s | Tighter timeouts + batch nutrition |

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| More concurrent API calls to Pexels/Unsplash | Rate limit handling already exists; parallel calls bounded to 6 |
| Redis cache adds dependency | Fallback to direct DB lookup if Redis unavailable |
| Tighter timeouts may increase failures | Graceful degradation returns partial results |
| Cache warm-up period | Image cache pre-warming via background job (existing pending queue) |

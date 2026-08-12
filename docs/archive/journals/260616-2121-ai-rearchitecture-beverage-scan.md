# AI Rearchitecture & Beverage Scan — Change Summary

**Date:** 2026-06-16  
**Branch:** `delivery`  
**PRs merged:** #354, #355, #356, #361, #362  
**Tests:** 1651 passing  
**Mobile impact:** zero — same API surface, same response shapes

---

## What Changed and Why

Three goals shipped together:

1. **Consolidate the AI layer** — replace 5+ overlapping Gemini classes with one `GeminiService` singleton
2. **Add beverage scan** — detect branded drinks from a photo, log nutrition to `hydration_entries`
3. **Single source of truth for drinks** — `hydration_entries` table owns all drink data; calorie aggregates include it

---

## Phase 1 — Dead Code Cleanup (PR #354)

**Problem:** `AnalyzeMealImageByUrlEvent` was registered in the event bus but never used. `GPTResponseParser` was misnamed (it called Gemini, not GPT).

**Changes:**
- Deleted `AnalyzeMealImageByUrlEvent` and its handler from `event_bus.py`
- Renamed `GPTResponseParser` → `VisionResponseParser` (file: `src/domain/parsers/vision_response_parser.py`)
- Deleted `src/app/commands/meal/analyze_meal_image_by_url_command.py` and its handler

---

## Phase 2 — AI Core Consolidation (PRs #355, #356)

**Problem:** Gemini was called through 4 different paths — `AIModelManager`, `GeminiModelManager`, `GeminiProvider`, and `GeminiCacheManager` — all doing overlapping things with inconsistent retry/fallback logic.

**What was built:**

### `src/infra/ai/gemini_service.py` (new, 561 lines)
Single singleton replacing all four managers. Exposes:
- `vision(purpose, image_bytes, prompt, ...)` — image + prompt → dict
- `text_json(purpose, user_prompt, system_prompt, ...)` — text → dict

Internally handles: LangChain model pool (TTL+LRU cache), circuit breaker, context cache integration, fallback chain across model tiers.

### `src/infra/ai/model_config.py`
Centralised fallback chains per `ModelPurpose` enum. Removed scattered `MODEL_NAME` constants from individual services.

### `src/infra/ai/circuit_breaker.py`
Extracted `ProviderCircuitBreaker` from old manager. Tracks per-model failure counts; filters unavailable models from the chain before each call.

### `src/infra/services/ai/gemini_cache_manager.py`
Added `wire_to_gemini_service()` method — infra→infra wiring that injects the cache manager into `GeminiService` at startup without the API layer importing infra directly.

### `src/api/main.py` + `src/api/base_dependencies.py`
- Removed direct `from src.infra.ai.gemini_service import GeminiService` import from API layer (was an architecture violation)
- Startup now calls `gemini_cache_manager.wire_to_gemini_service()` instead

### Prompt registry (`src/infra/services/ai/prompts/`)
System prompts extracted into `src/domain/services/prompts/system_prompts.py`. `VisionAIService` and `MealGenerationService` both pull from the same registry.

### `src/infra/adapters/ai_json_utils.py`
Canonical JSON extractor shared by all AI adapters. Replaces three independent regex-based extractors that diverged over time.

**Architecture rule enforced:** `src.api` must NOT import `src.infra` directly. Verified by CI contract check on every PR.

---

## Phase 3 — Beverage Scanning + Single-Source Persistence (PRs #361, #362)

### 3a — Gemini prompt + response contract

**`src/domain/model/ai/nutrition_contracts.py`** — Extended `VisionNutritionResponse` with optional `BeverageMetadata`:
```python
class BeverageMetadata(BaseModel):
    brand: str | None
    drink_name: str
    container_ml: int | None
    kcal_total: float
    sugar_g_total: float
    protein_g_total: float
    carbs_g_total: float
    fat_g_total: float
    hydration_weight: float
    label_source: Literal["ocr", "estimate"]
```

**`src/domain/services/prompts/system_prompts.py`** — Added beverage detection section to the vision system prompt. Gemini now identifies branded drinks by their label and returns totals (not per-100ml rates).

**`src/infra/adapters/vision_ai_service.py`** — Fixed `_to_legacy_vision_payload()` which was silently dropping `beverage_metadata` from Gemini's response (it was only returning `is_food/dish_name/foods/confidence`). One-line fix unblocked the entire scan path.

### 3b — Upload handler beverage routing

**`src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`**

Added `_handle_beverage_scan()` path. When `structured_data["beverage_metadata"]` is present, the handler:
1. Resolves the drink volume via container heuristics (uses `container_ml` from AI, falls back to catalog default)
2. Calls `HydrationWriteService.log_caloric_drink()` → writes to `hydration_entries`
3. Returns a response shaped like a meal scan (same fields, `source="beverage_scan"`) — mobile sees no difference

Added missing imports that were dropped during a merge: `from src.domain.model.nutrition.macros import Macros` and `from src.domain.model.nutrition.nutrition import Nutrition`.

### 3c — Hydration entries in all calorie aggregates (PR #362)

**Problem:** Three calorie-aggregation handlers only read the `meals` table. After Phase 3d (dual-write removal), drinks logged via `LogCaloricDrinkCommand` would be invisible in the feed and uncounted in weekly/daily budgets.

**Dedup algorithm** (shared across all three handlers):
```python
meal_id_set = {m.meal_id for m in <week/day meals>}
for entry in hydration_entries:
    if entry.legacy_meal_id and entry.legacy_meal_id in meal_id_set:
        continue  # already counted via old meal row
    # include entry
```
- `legacy_meal_id` is set on entries created during Phase 3d's dual-write window → skipped (meal row already counted)
- `legacy_meal_id = None` on entries created after dual-write removal → included
- Old entries only in `meals` (pre-dual-write) → not in `hydration_entries` → picked up by existing meals loop unchanged

**Files changed:**

`src/app/handlers/query_handlers/get_daily_activities_query_handler.py`
- After building meal activities from `meals` table, fetches `hydration_entries.find_by_date()` and appends non-duplicate entries
- New builder `_build_hydration_entry_activity()` returns same activity dict shape as `_build_hydration_activity()` (which served meals-table hydration rows)

`src/app/handlers/query_handlers/get_weekly_budget_query_handler.py`
- Fetches `hydration_entries.find_by_date_range()` alongside meals
- New `_sum_hydration()` closure mirrors `_sum_meals()` with the same date-bucketing and cheat-day exclusion logic
- New `_add_dicts()` helper combines meals + hydration totals for `consumed_total`, `consumed_before_today`, and `consumed_for_redistribution`

`src/app/handlers/query_handlers/get_nutrition_bulk_query_handler.py`
- Fetches hydration entries for the full date range; buckets by local date into `hydration_by_date`
- `_build_date_summary()` now accepts optional `hydration_entries` list; adds their macros to totals
- New `_get_hydration_date()` helper for local-date bucketing (mirrors existing `_get_meal_date()`)

`src/infra/repositories/hydration_repository_async.py`
- Added `find_by_date_range(user_id, start_date, end_date, user_timezone)` — was missing; only `find_by_date` existed

### 3d — Remove dual-write from LogCaloricDrinkCommandHandler

**`src/app/handlers/command_handlers/log_caloric_drink_command_handler.py`**
- Removed the `meals` table write that was creating a redundant meal row alongside every `hydration_entries` insert
- Response still returns a `meal_id`-shaped ID (now the `hydration_entries` ID) so mobile delete path works

### 3e — Hydration catalog virtual entry

**`src/domain/services/hydration_catalog_service.py`**
```python
DRINK_CATALOG["scanned"] = Drink(id="scanned", name="Scanned drink", ...)
```
Added after the `_DRINKS` list so it's resolvable via `find_by_id("scanned")` but excluded from `get_all()` (not shown in the catalog picker). Used as the `drink_id` for AI-scanned beverages whose nutrition comes from `BeverageScanParams`, not from catalog rates.

---

## Phase 4 — Observability + Docs (PRs #361, #362)

### Structured AI call logging

**`src/infra/ai/gemini_service.py`** — Every successful Gemini call now emits:
```
[AI-CALL] method=vision purpose=meal_scan model=gemini-2.0-flash latency_ms=1243 retry_count=0 fallback_used=False
```
Fields: `method`, `purpose`, `model`, `latency_ms`, `retry_count`, `fallback_used`. Replaces the old sparse fallback-only log.

### Migration

**`migrations/versions/20260616000001_add_beverage_columns_to_hydration_entry.py`**  
Added `image_url VARCHAR(512)` column to `hydration_entries` — stores the S3 URL of the scanned beverage photo.

### New docs

**`docs/beverage-scan.md`** — End-to-end flow, `BeverageMetadata` contract table, volume heuristics, hydration weight table, dedup algorithm, `[AI-CALL]` log format, eval set instructions.

**`scripts/development/cleanup_orphan_hydration_meal_rows.py`** — Dry-run-by-default script that can delete redundant dual-write meal rows after Phase 3d is stable in prod. **Not run yet — safe to defer indefinitely** since Phase 3c handles both old and new data correctly.

---

## Data Invariants (unchanged)

| Rule | Where enforced |
|------|---------------|
| Calories = `P×4 + (C−fiber)×4 + fiber×2 + F×9` | `Macros.total_calories`; `HydrationEntry.calories` property |
| Backend is sole calorie source | All aggregates use domain formula; mobile never re-derives |
| Weekly `remaining_days` includes today | `WeeklyBudgetService` (untouched) |

---

## What Did NOT Change

- All existing API routes and response schemas — mobile requires zero updates
- Barcode scan path — unchanged
- `WeeklyBudgetService` redistribution/skip logic — untouched
- `legacy_meal_id` column on `hydration_entries` — kept; will be dropped in a follow-up migration after one release cycle

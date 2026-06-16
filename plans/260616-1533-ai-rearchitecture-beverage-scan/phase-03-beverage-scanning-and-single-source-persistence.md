---
phase: 3
title: "Beverage Scanning and Single-Source Persistence"
status: pending
priority: P1
effort: "3-5d"
dependencies: [2]
---

# Phase 3: Beverage Scanning and Single-Source Persistence

## Overview

Upgrade vision prompt + contract to recognize packaged beverages; route beverage scans into `hydration_entries` only; unify the activities feed to read both tables; remove the dual-write from `LogCaloricDrinkCommand`. Ships in strict sub-PR order (3a → 3b → 3c → 3d → 3e).

**CRITICAL ship order**: 3c (feed reads both tables + all calorie aggregates updated) must be live before 3d (caloric catalog stops dual-writing). Violating this order leaves drink kcal invisible in budget/calendar views.

## Context Links

- Contract to extend: `src/domain/model/ai/nutrition_contracts.py` (`VisionNutritionResponse`, validator at line 105-110)
- Prompt to upgrade: `src/domain/services/prompts/system_prompts.py` (`VISION_ANALYSIS`)
- DB model to extend: `src/infra/database/models/hydration_entry.py`
- Scan handler: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Activities handler: `src/app/handlers/query_handlers/get_daily_activities_query_handler.py` (dedup ref: macros handler at line 68-99)
- Bulk activities: `src/app/handlers/query_handlers/get_bulk_activities_query_handler.py`
- Weekly budget: `src/app/handlers/query_handlers/get_weekly_budget_query_handler.py:328-357` (`_sum_meals()`)
- Bulk nutrition: `src/app/handlers/query_handlers/get_nutrition_bulk_query_handler.py:67-83` (`_build_date_summary()`)
- Macros handler (has correct guard already): `src/app/handlers/query_handlers/get_daily_macros_query_handler.py:68-99`
- Caloric drink handler: `src/app/handlers/command_handlers/log_caloric_drink_command_handler.py`
- Hydration catalog: `src/domain/services/hydration_catalog_service.py`
- Hydration query: `src/app/queries/hydration/get_daily_hydration_query.py`
- Delete handler: `src/app/handlers/command_handlers/delete_hydration_entry_command_handler.py:50-58`
- Cache invalidation: `src/app/services/cache_invalidation_service.py` (`after_hydration_write` at line 116-146)
- Eval script: `scripts/development/evaluate_meal_analyze_prompt_candidates.py`

## Architecture

```
POST /v1/meals/image/analyze
  └─► UploadMealImageImmediatelyHandler
        └─► GeminiService.vision(MEAL_SCAN) → VisionNutritionResponse
              ├─ beverage_metadata.is_packaged_beverage = true  [is_food=False]
              │    └─► HydrationWriteService.write() → hydration_entries only
              │         └─► after_hydration_write() cache invalidation
              │         └─► synthesize meal-shaped response (meal_id="hydration:{id}")
              └─ normal food  [is_food=True, foods non-empty]
                   └─► existing meal persistence (unchanged)

GET /v1/activities
  └─► GetDailyActivitiesQueryHandler
        ├─► meals = uow.meals.find_by_date()
        ├─► meal_id_set = {m.id for m in meals}
        ├─► hydration = uow.hydration_entries.find_by_date()  ← NEW
        ├─► deduped_hydration = [e for e in hydration if e.legacy_meal_id not in meal_id_set]
        └─► merge into unified timeline
```

## Implementation Steps

### 3a — Extend contract and prompt (1 PR)

Run existing eval set FIRST to capture baseline non-beverage accuracy.

1. Add `BeverageMetadata` Pydantic model to `nutrition_contracts.py`:
   ```python
   class BeverageMetadata(BaseModel):
       is_packaged_beverage: bool
       brand: str | None = Field(None, max_length=100)      # [F8] bounded
       product_name: str | None = Field(None, max_length=100)  # [F8] bounded
       container_type: Literal["can", "bottle", "cup", "carton", "unknown"]
       volume_ml: int | None
       sugar_per_100ml: float | None = Field(None, ge=0)
       kcal_per_100ml: float | None = Field(None, ge=0)     # [F10] float, not int
       label_source: Literal["nutrition_panel", "front_label", "estimate"]

   # Add to VisionNutritionResponse:
   beverage_metadata: BeverageMetadata | None = None
   ```

2. **[F1] Update `require_foods_for_food_images` validator** in `VisionNutritionResponse` to bypass when `beverage_metadata` is set:
   ```python
   @model_validator(mode="after")
   def require_foods_for_food_images(self) -> "VisionNutritionResponse":
       if (self.is_food
               and not self.foods
               and not (self.beverage_metadata and self.beverage_metadata.is_packaged_beverage)):
           raise ValueError("foods must contain at least one item when is_food is true")
       return self
   ```

3. Add `PACKAGED BEVERAGE DETECTION` section to `VISION_ANALYSIS` prompt in `system_prompts.py`:
   - **[F1]** Detection instructions: "For a packaged drink (can, bottle, carton, cup with a brand logo), set `is_food=false`, populate `beverage_metadata`, leave `foods` empty."
   - Brand reading from front label (Coca-Cola, Aquarius, Pocari Sweat, Pepsi, Red Bull, etc.) — `max 100 characters`.
   - Volume reading from label; fallback heuristics (can=330ml, slim can=250ml, small PET=500ml, large PET=1500ml).
   - Nutrition panel extraction for `kcal_per_100ml` / `sugar_per_100ml`; brand defaults when panel not visible (Coca-Cola Original ≈ 42 kcal/10.6g per 100ml, Aquarius Lemon ≈ 19/4.6, Pocari Sweat ≈ 25/6.2). **Set `label_source="estimate"` when using defaults.**
4. Append worked examples: Coca-Cola 330ml can (`is_food=false`), Aquarius 500ml PET, Pocari Sweat 500ml, chicken rice (`beverage_metadata=null`, `is_food=true`).
5. Bump `PROMPT_VERSION`.
6. Run eval set on upgraded prompt; **only merge if non-beverage accuracy unchanged**.

### 3b — Hydration-only persistence in scan handler (1 PR)

1. Add nullable columns to `HydrationEntry` DB model:
   - `brand VARCHAR(100)`, `product_name VARCHAR(100)` — **[F8] explicit length**
   - `kcal_per_100ml FLOAT`, `sugar_per_100ml FLOAT`, `image_url VARCHAR`
2. Generate Alembic migration (timestamp name). No backfill needed.
3. Extract `HydrationWriteService` in `src/domain/services/` — shared by scan handler and `LogCaloricDrinkCommandHandler`.
4. Modify `UploadMealImageImmediatelyHandler`:
   - If `beverage_metadata.is_packaged_beverage == True`:
     - **[F10] Null guard:** `kcal_per_100ml = bev.kcal_per_100ml or 0.0`, `sugar_per_100ml = bev.sugar_per_100ml or 0.0`.
     - Compute: `kcal = (bev.volume_ml or 0) * kcal_per_100ml / 100`, `sugar_g = (bev.volume_ml or 0) * sugar_per_100ml / 100`.
     - **[F12] Log WARNING when estimate:** `if bev.label_source == "estimate": logger.warning("beverage kcal is estimated", extra={brand, label_source, kcal_per_100ml})`.
     - **[F9] Conservative hydration_weight:** if `bev.label_source == "estimate"` and brand not in known catalog, default `hydration_weight = 0.7`. Otherwise: 0.7 (sugar>5g/100ml), 0.85 (sports drink pattern), 1.0 (confirmed water-only).
     - `HydrationWriteService.write(drink_id="scanned", brand, product_name, volume_ml, kcal_per_100ml, sugar_per_100ml, image_url, hydration_weight)`.
     - Synthesize meal-shaped response: `meal_id=f"hydration:{entry.id}"`, `meal_type="hydration"`, `source="hydration"`, `dish_name=brand`, `emoji="🥤"`, nutrition from entry.
     - **[F14] Cache invalidation:** call `cache_invalidation.after_hydration_write(user_id, log_date)` — NOT `after_meal_write` — so hydration ring cache keys are invalidated.
     - **No meal row written.**
   - Else: unchanged food path (`after_meal_write` unchanged).
5. Snapshot-test API response keys for beverage vs food scans.

### 3c — Unified activities feed and ALL calorie aggregates (1 PR — MUST ship before 3d)

**[F2] Extended scope:** Three calorie aggregation paths all read only `meals` and must be updated before 3d ships. Failure to update all three causes kcal to silently vanish from budget/calendar after dual-write removal.

1. Modify `GetDailyActivitiesQueryHandler`:
   - Fetch meals: `meals = await uow.meals.find_by_date(user_id, date)`.
   - **[F7] Explicit dedup algorithm:** `meal_id_set = {m.id for m in meals}`.
   - Fetch hydration: `hydration = await uow.hydration_entries.find_by_date(user_id, date)`.
   - Dedup: `deduped_hydration = [e for e in hydration if e.legacy_meal_id not in meal_id_set]`.
   - Merge `deduped_hydration` as `type="hydration"` items into timeline.
2. Apply same dedup pattern to `GetBulkActivitiesQueryHandler` and activities-presence query.
3. **[F13] Daily macros — do NOT remove existing guard:** `get_daily_macros_query_handler.py:68-99` already implements the correct `has_legacy_hydration` flag. Verify it is present and untouched. New scanned-beverage rows have no meal row → `has_legacy_hydration=False` → hydration_entries are already summed. **No code change needed here unless guard is absent.**
4. **[F2] Update `get_weekly_budget_query_handler.py:328-357` (`_sum_meals()`)**: add hydration_entries kcal/macro sum using the same `has_legacy_hydration` dedup pattern. This is mandatory before 3d.
5. **[F2] Update `get_nutrition_bulk_query_handler.py:67-83` (`_build_date_summary()`)**: add hydration_entries kcal/macro sum using the same dedup pattern. This is mandatory before 3d.
6. Integration test: assert `daily_kcal = meals.kcal + hydration_entries.kcal` for a test day with both food and beverage entries (pre-3d dual-write rows + new hydration-only rows).
7. Integration test: assert weekly budget remaining-calories includes beverage kcal.

### 3d — Remove dual-write from `LogCaloricDrinkCommand` (1 PR — after 3c)

1. Refactor `LogCaloricDrinkCommandHandler` to use `HydrationWriteService`; remove the `Meal` row creation.
2. Handler becomes: compute macros from catalog → `HydrationWriteService.write()` → return same response shape.
3. **[F6] Explicit `meal_id` mapping in response:** return `"meal_id": hydration_entry.id` (substituting hydration native id) so the field exists and the delete path at `delete_hydration_entry_command_handler.py` resolves by native id. Document this as a response-contract change in the PR description.
4. Integration test: assert exactly one `hydration_entries` row inserted and zero `meals` rows per caloric drink log.
5. Integration test: assert delete by the returned `meal_id` value succeeds (verifies delete handler resolves by hydration id).

### 3e — Catalog + DTO touch-ups and cleanup script (1 PR)

1. Add virtual `"scanned"` drink to `DRINK_CATALOG` in `hydration_catalog_service.py` — emoji 🥤, name "Scanned drink", `kcal_per_100ml=0.0` / `sugar_per_100ml=0.0` (placeholder; real values from entry row).
2. In `get_daily_hydration_query_handler.py` and activities feed mapper: when `drink_id="scanned"`, use stored `brand`/`product_name` for display title and stored per-100ml values — do not fall back to catalog placeholder.
3. Write one-shot cleanup script `scripts/development/cleanup_orphan_hydration_meal_rows.py`:
   - Dry-run by default; `--execute` flag required to delete.
   - Deletes `meals` rows where `meal_type="hydration"` AND `id IN (SELECT legacy_meal_id FROM hydration_entries WHERE legacy_meal_id IS NOT NULL)`.
   - Log count deleted.
4. **Note**: `legacy_meal_id` column drop is a follow-up migration after one release cycle — not in this plan.

### 3f — Beverage eval set (parallel with 3a–3e)

1. Build 10–20 image eval set using `scripts/development/evaluate_meal_analyze_prompt_candidates.py` infrastructure.
2. Images: Coca-Cola 330ml can, Aquarius 500ml PET, Pocari Sweat 500ml PET, Evian water bottle, beer can (333), tea bottle, juice carton, chicken rice bowl (negative), two more non-beverage negatives.
3. Assert: brand ±exact match, volume ±10ml, kcal/sugar ±15%.

## Related Code Files

- Modify: `src/domain/model/ai/nutrition_contracts.py` (add `BeverageMetadata`; update validator)
- Modify: `src/domain/services/prompts/system_prompts.py`
- Modify: `src/infra/database/models/hydration_entry.py`
- Create migration: `alembic/versions/{timestamp}_add_beverage_columns_to_hydration_entry.py`
- Create: `src/domain/services/hydration_write_service.py`
- Modify: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Modify: `src/app/handlers/query_handlers/get_daily_activities_query_handler.py`
- Modify: `src/app/handlers/query_handlers/get_bulk_activities_query_handler.py`
- Modify: `src/app/handlers/query_handlers/get_weekly_budget_query_handler.py` (add hydration_entries sum) ← **[F2]**
- Modify: `src/app/handlers/query_handlers/get_nutrition_bulk_query_handler.py` (add hydration_entries sum) ← **[F2]**
- Modify: `src/app/handlers/command_handlers/log_caloric_drink_command_handler.py`
- Modify: `src/domain/services/hydration_catalog_service.py`
- Modify: `src/app/queries/hydration/get_daily_hydration_query.py` (display mapper)
- Create: `scripts/development/cleanup_orphan_hydration_meal_rows.py`

## Success Criteria

- [ ] Manual scan of Coca-Cola 330ml can: `brand="Coca-Cola"`, `volume_ml=330`, kcal within ±15%. Response has `is_food=false`.
- [ ] Manual scan of Aquarius 500ml PET: `brand="Aquarius"`, `volume_ml=500`, kcal within ±15%.
- [ ] Manual scan of Pocari Sweat 500ml: `brand="Pocari Sweat"`, `volume_ml=500`, kcal within ±15%.
- [ ] Manual scan of plain water bottle: `is_packaged_beverage=true`, kcal=0 or near-zero.
- [ ] Manual scan of chicken rice bowl: `beverage_metadata=null`, `is_food=true`, normal food path.
- [ ] API response shape for beverage scan: `meal_id` field present (as `"hydration:{entry.id}"`).
- [ ] Activities timeline shows: scanned Coca-Cola, water via catalog, milk-tea via catalog — all with correct kcal in daily total.
- [ ] Weekly budget remaining-calories includes beverage kcal (integration test).
- [ ] Bulk nutrition calendar includes beverage kcal (integration test).
- [ ] Exactly one DB row per logged drink (integration test: `meals` delta = 0, `hydration_entries` delta = 1).
- [ ] Hydration cache ring updates immediately after beverage scan (no stale TTL window).
- [ ] Delete by returned `meal_id` succeeds for a 3d-logged drink.
- [ ] Validator test: `VisionNutritionResponse(is_food=True, foods=[], beverage_metadata=BeverageMetadata(is_packaged_beverage=True, ...))` passes Pydantic validation.
- [ ] `label_source="estimate"` entries emit WARNING log.
- [ ] No regressions in food-scan tests; eval-set non-beverage accuracy unchanged.
- [ ] Beverage eval set: 10–20 images, brand ±exact, volume ±10ml, kcal/sugar ±15%.
- [ ] `legacy_meal_id` column still present (drop is follow-up).

## Risk Assessment

High complexity, medium-high risk. Two critical sequencing constraints: (1) 3c must be fully live before 3d, (2) all three calorie-aggregation handlers (`weekly_budget`, `nutrition_bulk`, `daily_macros`) must read hydration_entries before 3d removes the dual-write rows. The dedup algorithm (meal_id_set filter) and the `has_legacy_hydration` guard in the macros handler must not be removed — they are load-bearing during the overlap window.

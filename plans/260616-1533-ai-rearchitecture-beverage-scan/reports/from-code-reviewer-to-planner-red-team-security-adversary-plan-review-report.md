# Red Team: Security Adversary Plan Review

**Plan:** AI Rearchitecture and Beverage Scan  
**Reviewed:** 2026-06-16  
**Reviewer lens:** Security Adversary (auth bypass, injection, data exposure, trust boundaries)

---

## Finding 1: `VisionNutritionResponse` validator rejects valid beverage scans — blind AI output trust fallback

- **Severity:** Critical
- **Location:** Phase 3, section "3a — Extend contract and prompt"
- **Flaw:** The plan adds `beverage_metadata` with `is_packaged_beverage=True` and `foods=[]` (empty). The existing `VisionNutritionResponse.require_foods_for_food_images` validator fires `ValueError` when `is_food=True AND foods=[]`. For a packaged beverage, Gemini is instructed to return `foods=[]`, but `is_food` will likely be `True` (beverages are consumable). The plan does not update this validator.
- **Failure scenario:** User scans a Coca-Cola can. Gemini returns `is_food=true, foods=[], beverage_metadata={is_packaged_beverage=true}`. Pydantic raises `ValueError: foods must contain at least one item when is_food is true`. Scan fails with 500 or validation error. Attacker can force this path on any beverage to trigger server errors.
- **Evidence:** `src/domain/model/ai/nutrition_contracts.py:106-110` — `require_foods_for_food_images` unconditionally rejects `is_food=True` with empty `foods`. Phase 3a plan text shows `foods` is set to empty list for beverages but does not mention updating this validator.
- **Suggested fix:** Phase 3a must add `OR beverage_metadata is not None AND beverage_metadata.is_packaged_beverage` as a bypass in `require_foods_for_food_images`, OR set `is_food=False` for packaged beverages in the prompt contract (document the semantic clearly).

---

## Finding 2: `get_nutrition_bulk_query_handler` silently excludes beverage kcal after dual-write removal

- **Severity:** Critical
- **Location:** Phase 3, section "3d — Remove dual-write from `LogCaloricDrinkCommand`" and "3c — Unified activities feed"
- **Flaw:** `WeeklyBudgetService.calculate_weekly_consumed_async` reads only `uow.meals.find_by_date_range` — no `hydration_entries` query. `get_nutrition_bulk_query_handler._build_date_summary` iterates only `meals`. After 3d removes the dual-write meal row, all beverage kcal vanishes from the weekly budget calculation and from bulk nutrition summaries. The plan's Step 5 in 3c only mentions updating `GetDailyActivitiesQueryHandler` and `GetDailyMacrosQueryHandler`; it does not mention `WeeklyBudgetService` or `get_nutrition_bulk_query_handler`.
- **Failure scenario:** User logs Coca-Cola (138 kcal) via scan. 3d removes the meal row. WeeklyBudgetService sums the week — those 138 kcal are invisible. Weekly "remaining calories" calculation is permanently overstated after every beverage log. User eats over budget without the app detecting it.
- **Evidence:**
  - `src/domain/services/weekly_budget_service.py:128-158` — `calculate_weekly_consumed_async` only queries `uow.meals`; no hydration_entries.
  - `src/app/handlers/query_handlers/get_nutrition_bulk_query_handler.py:67-83` — `_build_date_summary` iterates only `meals_by_date`; no hydration_entries branch.
  - Phase 3c Step 5 says "Update daily nutrition aggregate" but names only `GetDailyMacrosQueryHandler` and `GetDailyActivitiesQueryHandler`; no mention of `WeeklyBudgetService` or `GetNutritionBulkQueryHandler`.
- **Suggested fix:** Phase 3c must explicitly list `WeeklyBudgetService.calculate_weekly_consumed_async` and `GetNutritionBulkQueryHandler._build_date_summary` as required changes. Both must gain the same `has_legacy_hydration` dedup pattern that `get_daily_macros_query_handler.py:68-99` already implements.

---

## Finding 3: `UserContextAwareAnalysisStrategy` is an active caller path — Phase 2d deletion would break beverage scan

- **Severity:** High
- **Location:** Phase 2, section "2d — Reduce vision strategies"
- **Flaw:** Phase 2d says "Verify call sites of `CombinedAnalysisStrategy` and `UserContextAwareAnalysisStrategy` — confirm unused. Delete unused strategies." `UserContextAwareAnalysisStrategy` is **not** unused. `UploadMealImageImmediatelyHandler` (the scan handler targeted in Phase 3) calls `AnalysisStrategyFactory.create_user_context_strategy()` which returns a `UserContextAwareAnalysisStrategy`. Deleting it in Phase 2d then running Phase 3 on the same handler is a live defect.
- **Failure scenario:** After Phase 2d deletes `UserContextAwareAnalysisStrategy`, any meal scan with `user_description` parameter (`POST /v1/meals/image/analyze?user_description=no+sugar`) hits a `NameError` or `AttributeError` at runtime. This path is used by paying users adding food context to their scans.
- **Evidence:**
  - `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py:78-86` — active call: `AnalysisStrategyFactory.create_user_context_strategy(command.user_description)`.
  - `src/domain/strategies/meal_analysis_strategy.py:192-268` — `UserContextAwareAnalysisStrategy` defined and returned by factory.
  - `src/infra/adapters/vision_ai_service.py:346-406` — multiple callers of the factory; `create_user_context_strategy` is not called here but factory itself is active.
- **Suggested fix:** Phase 2d's "confirm unused" step will fail for `UserContextAwareAnalysisStrategy`. The plan must either keep this strategy (just slim it to `{prompt, schema, purpose}` return like other strategies) or migrate the `user_description` path first.

---

## Finding 4: `BeverageMetadata.brand` / `product_name` from AI output written to DB without length bounds or sanitization

- **Severity:** High
- **Location:** Phase 3, section "3a — Extend contract and prompt" and "3b — Hydration-only persistence in scan handler"
- **Flaw:** The plan adds `brand: str | None` and `product_name: str | None` to `BeverageMetadata` with no `max_length` constraints. These AI-generated strings will be written to `hydration_entries.brand VARCHAR` and `product_name VARCHAR`. The existing contract fields all have explicit `max_length` (`dish_name: max_length=200`, `name: max_length=200`). Gemini is instructed to read brand from "front label" — a compromised or adversarially crafted image could elicit a 10KB string that blows up the VARCHAR column or gets reflected back into mobile responses verbatim.
- **Failure scenario 1:** Attacker crafts a beverage label with a 50 000-char brand string. Gemini returns it. `BeverageMetadata` accepts it (no max_length). `hydration_entries.brand` is a plain `VARCHAR` without explicit length limit in the current model (SQLAlchemy `String(64)` for `drink_id`, but the new `brand` column will be `VARCHAR` without plan-specified length). PostgreSQL truncates or raises on insert depending on column definition.
- **Failure scenario 2:** AI-generated brand string containing HTML/JS (`<script>alert(1)</script>`) is stored in DB and returned in the activities feed as `"title"` — potential XSS if the mobile or web client renders it without escaping.
- **Evidence:**
  - `src/domain/model/ai/nutrition_contracts.py:80-83, 97` — all existing string fields have `max_length`; the plan's proposed `BeverageMetadata` fields do not specify any.
  - Phase 3b Step 1: `brand VARCHAR, product_name VARCHAR` — no explicit length in the migration spec.
  - `src/app/handlers/query_handlers/get_daily_activities_query_handler.py:151-217` — meal title flows directly from `meal.dish_name` / `meal.source` into the activities response without sanitization.
- **Suggested fix:** Add `max_length=100` to `brand` and `product_name` in `BeverageMetadata`. Set explicit column length in migration (`VARCHAR(100)`). Add the same `_strip_required_text` validator pattern used on existing `VisionFoodEstimate.name`.

---

## Finding 5: Hydration weight (0.7 / 0.85 / 1.0) derived from Gemini-controlled `sugar_per_100ml` — AI controls a trust-level flag

- **Severity:** High
- **Location:** Phase 3, section "3b — Hydration-only persistence in scan handler"
- **Flaw:** Phase 3b assigns `hydration_weight` based on `sugar_per_100ml > 5g` (sweetened → 0.7) or an inferred "sports drink" classification — both values come from `BeverageMetadata` which is derived from Gemini output. `hydration_weight` is stored in `hydration_entries.credited_ml` (computed as `volume_ml * hydration_weight`). An adversary can manipulate the scanned label image to force Gemini to return `sugar_per_100ml=0`, classifying a sugary drink as water-equivalent (weight=1.0), inflating daily hydration credit and underreporting sugar intake.
- **Failure scenario:** Attacker scans a Coca-Cola can with an obscured nutrition panel. Gemini cannot read the panel, uses `label_source="estimate"` fallback of `42 kcal/10.6g per 100ml`. If the attacker provides a custom label image with a forged nutrition panel showing `sugar=0`, Gemini returns `sugar_per_100ml=0`. Handler assigns `hydration_weight=1.0`. The 330ml Coca-Cola gets `credited_ml=330` instead of 231. Daily water goal is met faster; sugar intake is hidden.
- **Evidence:**
  - Phase 3b Step 4: `hydration_weight: 0.7 (sweetened/sugar>5g/100ml), 0.85 (sports drink), 1.0 (water)` — classification logic driven purely by AI output.
  - `src/domain/model/hydration/drink.py:37` — `credited_ml = int(ml * hydration_weight + 0.5)` — hydration_weight directly controls credited hydration.
  - `src/domain/services/hydration_catalog_service.py:100` — existing catalog hard-codes `hydration_weight=0.70` for milk tea; there is no AI-path equivalent validation.
- **Suggested fix:** For scanned beverages, compute `hydration_weight` from the catalog's brand-matched entry if available; only fall back to AI-derived sugar value when brand is unknown. Add a hard cap: if `label_source="estimate"` and brand is unknown, default to `hydration_weight=0.7` (conservative / sweetened assumption) rather than trusting AI sugar value.

---

## Finding 6: `kcal_per_100ml=None` path in scan handler produces division/multiplication of `None` — unhandled null

- **Severity:** High
- **Location:** Phase 3, section "3b — Hydration-only persistence in scan handler"
- **Flaw:** Phase 3b Step 4 shows: `kcal = volume_ml × kcal_per_100ml / 100`. `BeverageMetadata.kcal_per_100ml: int | None` — it is explicitly nullable. If Gemini cannot see the nutrition panel and returns `kcal_per_100ml=None`, the computation `volume_ml × None / 100` raises `TypeError` in Python. The plan has no null guard here.
- **Failure scenario:** User scans a beer can from an angle where the nutrition panel is not visible. Gemini returns `kcal_per_100ml=None`. Handler executes `kcal = 330 * None / 100` → `TypeError`. Unhandled exception propagates. Scan fails with 500. Retry loop (if any) fires again; Cloudinary image already uploaded; orphan image remains.
- **Evidence:**
  - Phase 3a Step 1: `kcal_per_100ml: int | None` — explicitly nullable in plan's `BeverageMetadata` definition.
  - Phase 3b Step 4: `Compute: kcal = volume_ml × kcal_per_100ml / 100` — no null check mentioned.
  - Existing `log_caloric_drink_command_handler.py:60-62` pattern: `kcal_per_100ml` is never `None` there because catalog entries have hard values (`src/domain/services/hydration_catalog_service.py:98-111`).
- **Suggested fix:** Add a null guard: `if kcal_per_100ml is None: kcal_per_100ml = 0` (or fall back to brand-catalog default). Add a Pydantic `ge=0` constraint and consider making it `float | None` to prevent type errors on decimal values (e.g. 42.1 kcal).

---

## Finding 7: Bulk nutrition query (`get_nutrition_bulk`) never reads `hydration_entries` — silent kcal undercount persists post-3d

- **Severity:** High
- **Location:** Phase 3, section "3c — Unified activities feed"
- **Flaw:** This is the calendar/week-view caloric summary path. `get_nutrition_bulk_query_handler._build_date_summary` sums kcal from `meals` only (line 181-195). After 3d removes the dual-write, caloric drinks have zero meal rows; their kcal is invisible to this handler. The plan's 3c Step 5 lists "Update daily nutrition aggregate" but names only `GetDailyMacrosQueryHandler` — `GetNutritionBulkQueryHandler` is not in the plan's scope.
- **Failure scenario:** After 3d ships, the mobile weekly calendar view shows every day's caloric drink kcal as zero. If a user drinks 300 kcal/day in beverages, the weekly summary shows 2100 kcal/week phantom deficit. The weekly budget redistributes incorrectly.
- **Evidence:**
  - `src/app/handlers/query_handlers/get_nutrition_bulk_query_handler.py:67-83` — only `meals.find_by_date_range`; no hydration_entries read.
  - Phase 3c Step 5: names `GetDailyActivitiesQueryHandler` and `GetDailyMacrosQueryHandler` only.
  - Phase 3 Related Code Files list (`get_bulk_activities_query_handler` is listed, `get_nutrition_bulk_query_handler` is NOT).
- **Suggested fix:** Add `GetNutritionBulkQueryHandler` to Phase 3c's required changes. Apply the same `has_legacy_hydration` dedup + hydration_entries sum pattern. Ship this as part of 3c (not 3d).

---

## Finding 8: `label_source` brand-default values hard-coded in the prompt — Gemini can hallucinate wrong defaults for unknown brands, inflating user kcal

- **Severity:** Medium
- **Location:** Phase 3, section "3a — Extend contract and prompt"
- **Flaw:** Phase 3a Step 2 instructs the prompt to embed brand-specific kcal defaults (Coca-Cola ≈ 42 kcal/100ml, Aquarius ≈ 19, Pocari ≈ 25). When Gemini sees an unknown brand but the label is partially obscured, it may pattern-match to the nearest known brand and apply that brand's defaults, producing a quietly wrong kcal estimate. Crucially, `label_source: "estimate"` is the only signal distinguishing a measured vs guessed value — but the plan does not require the handler to log a warning or degrade confidence when `label_source="estimate"`.
- **Failure scenario:** Adversarial or degraded image of an energy drink with 250 kcal/100ml (e.g. Monster Ultra Energy). Gemini picks the closest brand from its defaults (Coca-Cola, 42 kcal) and returns `label_source="estimate"`. Handler stores 139 kcal (42 × 330/100) instead of 825 kcal. User's kcal tracking is massively wrong; no alert is generated. The `label_source` flag goes into DB but the handler does nothing with it.
- **Evidence:**
  - Phase 3a Step 2: "brand defaults when panel not visible (Coca-Cola Original ≈ 42 kcal/10.6g per 100ml, Aquarius Lemon ≈ 19/4.6, Pocari Sweat ≈ 25/6.2)" — these are prompt-embedded, not validated against catalog.
  - Phase 3b Step 4: handler uses `kcal_per_100ml` from AI response directly with no check on `label_source`.
  - Phase 3e Step 2 only uses `brand`/`product_name` for display title, not for kcal correction.
- **Suggested fix:** When `label_source="estimate"`, log at WARNING level and zero-fill kcal or apply catalog lookup. Do not silently use AI-estimated kcal as ground truth for diet tracking.


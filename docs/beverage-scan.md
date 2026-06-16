# Beverage Scan

AI-powered packaged-beverage detection routed to `hydration_entries` instead of meals.

## Endpoint

- `POST /v1/meals/image/analyze` — direct multipart scan.
- `POST /v1/meals/scan-by-url` — Cloudinary URL scan after direct mobile upload.

Both endpoints keep the existing meal-shaped response.

## End-to-End Flow

```
Mobile → POST /v1/meals/image/analyze or /v1/meals/scan-by-url
         ↓
UploadMealImageImmediatelyHandler or ScanByUrlCommandHandler
  1. Get image bytes (multipart upload or Cloudinary URL download)
  2. GeminiService.vision(MEAL_SCAN, image_bytes, VISION_ANALYSIS prompt)
  3. VisionAIService._to_legacy_vision_payload() → includes beverage_metadata
  4. bev_meta = structured_data.get("beverage_metadata")
  5. if bev_meta.is_packaged_beverage → hydration-only scan path
     else → normal food path

hydration-only scan path
  1. build_beverage_scan_params(bev_meta) → BeverageScanParams
  2. Save HydrationEntry(id=<uuid>, drink_id="scanned", legacy_meal_id=None, source="scan_beverage")
  3. Invalidate hydration caches (not meal caches)
  4. Return transient Meal-shaped response with meal_id=<hydration_entry.id> and meal_type="hydration"
```

For mobile backward compatibility, `GET /v1/meals/{meal_id}` and
`DELETE /v1/meals/{meal_id}` also resolve hydration-only scanned beverage IDs.
This keeps existing detail/delete flows working while avoiding a persisted
compatibility row in `meals`.

## BeverageMetadata Contract

Gemini returns this when `is_packaged_beverage=true`:

```json
{
  "is_packaged_beverage": true,
  "brand": "Coca-Cola",
  "product_name": "Coca-Cola Original",
  "volume_ml": 330,
  "kcal_per_100ml": 42.0,
  "sugar_per_100ml": 10.6,
  "label_source": "label"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `is_packaged_beverage` | bool | True → route to hydration path |
| `brand` | str (max 100) | Brand or product name for display |
| `product_name` | str (max 100) | Fallback for brand |
| `volume_ml` | int | Container volume read from label |
| `kcal_per_100ml` | float | Caloric density (nullable → 0) |
| `sugar_per_100ml` | float | Sugar density (nullable → 0) |
| `label_source` | str | `"label"` or `"estimate"` |

## BeverageScanParams (domain)

Stores computed totals, not per-100ml rates:

```python
kcal_total = volume_ml * kcal_per_100ml / 100
sugar_g_total = volume_ml * sugar_per_100ml / 100
hydration_weight = compute_hydration_weight(label_source, sugar_per_100ml)
```

## Volume Heuristics

If Gemini cannot read the label volume, the prompt instructs it to estimate:

| Container | Default ml |
|-----------|-----------|
| Can | 330 |
| Small bottle | 500 |
| Large bottle | 1000 |
| Cup/carton (unknown) | 330 |

## Hydration Weight Table

| Condition | Weight |
|-----------|--------|
| `label_source = "label"` and sugar = 0g/100ml | 1.00 |
| `label_source = "label"` and sugar > 0–5g/100ml | 0.85 |
| `label_source = "label"` and sugar > 5g/100ml | 0.70 |
| `label_source = "estimate"` (any sugar) | 0.70 (conservative) |

## Deduplication in Feeds

`HydrationEntry.legacy_meal_id` links old dual-write entries to a corresponding Meal row:

- **Pre-Phase-3d entries** (LogCaloricDrink dual-write): `legacy_meal_id` set → Meal row exists → feed reads via Meal
- **Post-Phase-3d entries** (LogCaloricDrink hydration-only): `legacy_meal_id = None` → feed reads via HydrationEntry
- **Beverage scan entries**: `legacy_meal_id = None` → feed reads via HydrationEntry

Dedup algorithm used in activities feed and calorie aggregates:
```python
meal_id_set = {m.meal_id for m in meals}
new_entries = [e for e in hydration_entries if e.legacy_meal_id not in meal_id_set]
```

## Observability

GeminiService emits per-call structured logs:
```
[AI-CALL] method=vision purpose=MEAL_SCAN model=gemini-2.5-flash-lite latency_ms=1240 retry_count=0 fallback_used=False
```

Beverages with estimated nutrition log a WARNING:
```
[BEVERAGE-KCAL-ESTIMATE] drink=Unknown kcal_total=0.0 label_source=estimate
```

## Eval Set

Use `scripts/development/evaluate_meal_analyze_prompt_candidates.py` to run the beverage prompt against test images. Eval set should include:
- Coke can (label visible)
- Smoothie bottle (partial label)
- Water bottle (no nutrition panel)
- Non-beverage food (must NOT trigger beverage path)

# Beverage Scan — Developer Guide

**Last Updated:** June 16, 2026
**Prompt version:** `2026-06-16-bev` (`SystemPrompts.PROMPT_VERSION`)

---

## End-to-End Flow

```
POST /v1/meals/image/analyze
  └─► UploadMealImageImmediatelyCommandHandler
        ├─► Cloudinary upload → image_url
        └─► GeminiService.vision(MEAL_SCAN, image_bytes)
              └─► VisionNutritionResponse.beverage_metadata populated
                    └─► is_packaged_beverage=True branch
                          ├─► Meal row  (source="hydration", status=READY)
                          └─► HydrationEntry (drink_id="scanned", image_url, macros)
```

The handler (`src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`) checks `beverage_metadata.is_packaged_beverage` after the vision call and delegates to `_handle_beverage_scan()`. The API response shape is unchanged — callers receive a `Meal` domain object.

---

## Prompt Versioning

- `SystemPrompts.PROMPT_VERSION` is set in `src/domain/services/prompts/system_prompts.py`.
- Bump the date suffix (`YYYY-MM-DD-bev`) whenever the beverage detection section of the prompt changes.
- The version is embedded in AI request metadata for traceability.

---

## Key Data Contracts

### `BeverageMetadata` (`src/domain/model/ai/nutrition_contracts.py`)

| Field | Type | Notes |
|-------|------|-------|
| `is_packaged_beverage` | `bool` | Routing gate — triggers beverage branch |
| `brand` | `str \| None` | Brand name from label |
| `product_name` | `str \| None` | Product name; used as drink name if brand absent |
| `container_type` | `Literal[can, bottle, cup, carton, unknown]` | Used for volume inference |
| `volume_ml` | `int \| None` | AI-reported volume; falls back to heuristic if absent |
| `sugar_per_100ml` | `float \| None` | Used for hydration weight calculation |
| `kcal_per_100ml` | `float \| None` | Used to derive macro totals |
| `label_source` | `Literal[nutrition_panel, front_label, estimate]` | Confidence signal |

### `HydrationEntry` (`src/infra/database/models/hydration_entry.py`)

| Column | Source |
|--------|--------|
| `drink_name_snapshot` | `brand` or `product_name` from AI response |
| `drink_id` | Hard-coded `"scanned"` |
| `image_url` | Cloudinary URL from upload step |
| `legacy_meal_id` | FK to the companion `Meal` row (`source="hydration"`) |
| `source` | `"scan_beverage"` |

---

## Volume Inference Heuristics

When the AI response omits `volume_ml`, these defaults apply (`build_beverage_scan_params` in `src/domain/services/hydration_write_service.py`):

| Container type | Default volume |
|----------------|---------------|
| Slim can | 250 ml |
| Standard can | 330 ml |
| Small PET bottle | 500 ml |
| Large PET bottle | 1500 ml |
| Cup / carton | 250 ml |

---

## `hydration_weight` Assignment

Computed by `compute_hydration_weight(label_source, sugar_per_100ml)`:

| Condition | Weight | Rationale |
|-----------|--------|-----------|
| `label_source == "estimate"` | 0.7 | Conservative fallback — data unreliable |
| `sugar_per_100ml > 5` | 0.7 | High-sugar (Coke, juice) — counts less toward hydration |
| `0 < sugar_per_100ml ≤ 5` | 0.85 | Sports / low-sugar drinks |
| `sugar_per_100ml == 0` | 1.0 | Water-like — full hydration credit |

`credited_ml = int(volume_ml * hydration_weight)`

---

## Adding a Test Case to the Eval Set

The eval script lives at `scripts/development/evaluate_meal_analyze_prompt_candidates.py`. Cases use mocked response payloads (no real Gemini calls).

1. Open `_default_cases()` in the script.
2. Append a `PromptEvalCase`:

```python
PromptEvalCase(
    case_id="beverage-coca-cola",
    response_payload={
        "structured_data": {
            "is_food": True,
            "dish_name": "Coca-Cola",
            "foods": [],
            "confidence": 0.95,
            "beverage_metadata": {
                "is_packaged_beverage": True,
                "brand": "Coca-Cola",
                "container_type": "can",
                "volume_ml": 330,
                "sugar_per_100ml": 10.6,
                "kcal_per_100ml": 42.0,
                "label_source": "nutrition_panel",
            },
        }
    },
),
```

3. Run: `python scripts/development/evaluate_meal_analyze_prompt_candidates.py`
4. The script ranks prompt candidates by parse-success rate and token count.

---

See related: `external-services.md` → Google Gemini, `database-guide.md`

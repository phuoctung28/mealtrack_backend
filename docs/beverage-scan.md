# Beverage Scan

Meal image scan no longer has a packaged-beverage hydration route.

## Current Behavior

These meal endpoints treat visible edible or drinkable intake as normal meal
nutrition:

- `POST /v1/meals/image/analyze`
- `POST /v1/meals/scan-by-url`

Caloric drinks such as soda, juice, smoothies, and milk tea should be returned
as normal `foods` entries by the vision prompt and persisted as `Meal` rows with
`source="scanner"`.

Hydration logging remains explicit through `/v1/hydration/*`.

## Flow

```
Mobile → POST /v1/meals/image/analyze or /v1/meals/scan-by-url
         ↓
UploadMealImageImmediatelyHandler or ScanByUrlCommandHandler
  1. Get image bytes (multipart upload or Cloudinary URL download)
  2. For `scan_mode="food_label"`, call `VisionAIService.analyze_food_label(...)`
     and persist `Meal(source="food_label")`
  3. Otherwise call `VisionAIService.analyze(...)`
  4. Validate `is_food`
  5. Parse normal nutrition foods
  6. Persist `Meal(source="scanner")`
  7. Invalidate meal caches
```

Meal scan must not create `hydration_entries`.

## Prompt Contract

- `is_food=true` means the image contains visible edible or drinkable intake.
- Ambiguous but likely edible/drinkable images should return `is_food=true`
  with lower confidence.
- Drinks should be represented as normal `foods` entries.
- `beverage_metadata` should remain `null` in meal scan output.
- True non-food images return `is_food=false` and are mapped to the existing
  not-food API error.

## Zero-Calorie Drinks

Water and other zero-calorie hydration drinks should be logged through
hydration endpoints. Meal scan does not silently route them into hydration.

The existing `has_food` guard rejects parsed output with no food items or zero
derived calories.

## Historical Compatibility

Older beverage-scan implementations created hydration-only rows with
`source="scan_beverage"` and no persisted meal row. Compatibility reads/deletes
for those existing IDs may remain in the codebase, but new meal scan requests
should not create new `scan_beverage` hydration rows.

## Validation

Keep upload and scan-by-url behavior aligned:

- Coke or milk tea image → normal meal row.
- Water image → no hydration side effect from meal scan.
- Laptop/shoe/person image → not-food rejection.
- Cropped pastry/display-case food → normal food scan with lower confidence.

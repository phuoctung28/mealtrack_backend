# Meal Catalog Import Schema

Product/content team owns a JSON manifest. Backend imports it into `meal_catalog`
and derives nutrition from `food_reference`.

## Required Shape

```json
{
  "release_key": "meal-catalog-2026-07",
  "expected_recipe_count": 180,
  "recipes": [
    {
      "recipe_key": "vietnamese-chicken-rice-001",
      "cuisine": "vietnamese",
      "name": "Vietnamese Chicken Rice",
      "description": "Optional short display copy",
      "image_url": "https://example.com/image.jpg",
      "meal_types": ["lunch", "dinner"],
      "ingredients": [
        {
          "food_reference_id": 123,
          "name": "Chicken breast",
          "quantity": 120,
          "unit": "g"
        },
        {
          "food_reference_id": null,
          "name": "White rice",
          "quantity": 150,
          "unit": "g"
        }
      ]
    }
  ]
}
```

## Field Rules

| Field | Required | Notes |
| --- | --- | --- |
| `release_key` | Yes | Human-readable batch label for file tracking. |
| `expected_recipe_count` | Yes | Usually `180` for production import. |
| `recipe_key` | Yes | Stable unique key. Do not reuse for changed content. |
| `cuisine` | Yes | `vietnamese`, `japanese`, or `korean`. |
| `name` | Yes | Display name shown in the app. |
| `description` | No | Short display-only text. |
| `image_url` | No | Public image URL. |
| `meal_types` | Yes | Any of `breakfast`, `lunch`, `dinner`, `snack`. |
| `ingredients[].food_reference_id` | No | Prefer exact ID. If `null`, importer matches by normalized `name`. |
| `ingredients[].name` | Yes | Used for display and lookup when ID is `null`. |
| `ingredients[].quantity` | Yes | Positive number. |
| `ingredients[].unit` | Yes | `g`, `kg`, `oz`, `ml`, `l`, or a serving unit in `food_reference`. |

Do not provide recipe servings, cooking instructions, calories, macro totals, or
ingredient `resolved_grams`. Backend calculates recipe protein, carbs, fat,
fiber, sugar, calories, and any needed gram conversion from
`food_reference_id`, `quantity`, and `unit` when catalog meals are read or
scored. These derived values are not stored in `meal_catalog` or
`meal_catalog_ingredients`.

## Import Commands

Validate and resolve only:

```bash
.venv/bin/python scripts/import_catalog_recipe_seeds.py \
  --manifest scripts/data/meal-recommendation-recipes.json \
  --dry-run \
  --resolver-report plans/reports/meal-catalog-resolver-report.json
```

Import into the configured database:

```bash
.venv/bin/python scripts/import_catalog_recipe_seeds.py \
  --manifest scripts/data/meal-recommendation-recipes.json
```

The import is additive. Exact duplicates are skipped. A reused `recipe_key` with
changed content fails so existing recommendation history is not rewritten.

## Ingredient Resolution

When `ingredients[].food_reference_id` is `null`, the importer tries:

1. Exact `food_reference.name_normalized` match.
2. Approved resolver map match.
3. Fuzzy candidate scoring for review.

Approved resolver map example:

```json
{
  "pork shoulder": 1425,
  "rice noodles": 845
}
```

Use it with:

```bash
.venv/bin/python scripts/import_catalog_recipe_seeds.py \
  --manifest scripts/data/meal-recommendation-recipes.json \
  --resolver-map scripts/data/meal-catalog-resolver-map.json \
  --resolver-report plans/reports/meal-catalog-resolver-report.json \
  --dry-run
```

The importer only auto-resolves verified food references above the configured
fuzzy threshold. Unverified or ambiguous candidates are written to the resolver
report for review.

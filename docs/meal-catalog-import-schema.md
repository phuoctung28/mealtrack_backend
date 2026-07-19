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

The current resolver is for **ingredient food-reference resolution**. It maps
`ingredients[].name` to `food_reference.id` so backend can calculate nutrition
from canonical food references.

It does not yet do fuzzy duplicate detection for meal names such as `Com Tam`
vs `Cơm Tấm Sườn`. Meal-level duplicate protection is currently exact:
`recipe_key` and `content_hash`.

When `ingredients[].food_reference_id` is `null`, the importer tries:

1. Exact `food_reference.name_normalized` match.
2. Approved resolver map match.
3. Fuzzy candidate scoring for review.

Resolution outcomes:

| Case | Behavior |
| --- | --- |
| `food_reference_id` is provided and exists | Use it directly. |
| `food_reference_id` is provided but missing | Import fails for that ingredient. |
| One verified exact normalized-name match | Auto-resolve. |
| Multiple verified exact matches | Report `ambiguous_exact_match`. |
| One exact match but not verified | Report `exact_match_not_verified`. |
| High-confidence verified fuzzy match | Auto-resolve when score is at least threshold and ahead of runner-up. |
| No safe match | Report `needs_review` with ranked candidates. |

Default fuzzy threshold is `0.92`. Fuzzy score combines name similarity and token
overlap, then penalizes extra candidate tokens. The auto-resolver only accepts a
candidate when it is at least `0.08` ahead of the runner-up.

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

## Resolver Workflow

Recommended first pass for a research-team file:

```bash
.venv/bin/python scripts/import_catalog_recipe_seeds.py \
  --manifest scripts/data/vn-user-common-meal-catalog.json \
  --partial \
  --dry-run \
  --resolver-report plans/reports/vn-user-common-meal-catalog-resolver-report.json
```

Use `--partial` when importing/testing fewer than the production default of 180
recipes. It validates against the actual recipe count and skips the exact
production cuisine split.

Review `plans/reports/vn-user-common-meal-catalog-resolver-report.json`.
Each issue looks like:

```json
{
  "recipe_index": 0,
  "recipe_key": "vn-user-common-pho-ga-001",
  "ingredient_index": 1,
  "ingredient_name": "rice noodles",
  "normalized_name": "rice noodles",
  "reason": "needs_review",
  "candidates": [
    {
      "food_reference_id": 845,
      "name": "Rice noodles",
      "name_normalized": "rice noodles",
      "source": "catalog_seed",
      "is_verified": true,
      "score": 0.91
    }
  ]
}
```

For every acceptable candidate, add an approved resolver map:

```json
{
  "rice noodles": 845,
  "pork shoulder": 1425,
  "fried egg": 233
}
```

Then rerun dry-run with the resolver map:

```bash
.venv/bin/python scripts/import_catalog_recipe_seeds.py \
  --manifest scripts/data/vn-user-common-meal-catalog.json \
  --partial \
  --dry-run \
  --resolver-map scripts/data/meal-catalog-resolver-map.json \
  --resolver-report plans/reports/vn-user-common-meal-catalog-resolver-report.json
```

When dry-run passes with `import=passed`, import into the configured database:

```bash
.venv/bin/python scripts/import_catalog_recipe_seeds.py \
  --manifest scripts/data/vn-user-common-meal-catalog.json \
  --partial \
  --resolver-map scripts/data/meal-catalog-resolver-map.json
```

After import, generate missing catalog image URLs through Cloudflare Workers AI:

```bash
.venv/bin/python scripts/generate_catalog_meal_images.py --limit 10
```

First test one prompt without calling Cloudflare:

```bash
.venv/bin/python scripts/generate_catalog_meal_images.py --limit 1 --dry-run
```

The tool reads `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, and optional
`CLOUDFLARE_WORKERS_AI_IMAGE_MODEL` from `.env`. It stores the returned
Cloudflare `result.image` URL in `meal_catalog.image_url`.

## Bootstrap Mode

For early MVP catalog loading, use best-effort mode when we want the importer to
resolve all possible ingredients without human review first:

```bash
.venv/bin/python scripts/import_catalog_recipe_seeds.py \
  --manifest scripts/data/vn-user-common-meal-catalog.json \
  --partial \
  --dry-run \
  --resolve-all-best-effort \
  --resolver-report plans/reports/vn-user-common-meal-catalog-resolver-report.json
```

In this mode, the resolver can pick unverified or unapproved-source candidates
and allows broader unit fallbacks. Use it to bootstrap a test catalog, not as the
final production-quality import policy.

## Duplicate Handling

Current duplicate handling is additive and history-safe:

| Duplicate type | Behavior |
| --- | --- |
| Same `recipe_key` and same resolved content hash | Skip existing row. |
| Same `content_hash` with different `recipe_key` | Skip existing row. |
| Same `recipe_key` but changed content | Fail import. |
| Similar meal name only | Not detected yet. |

If product sends near-duplicate meal names, the current importer may allow them
when `recipe_key` and content hash are different. Add a meal-name duplicate
resolver before large production imports if this becomes noisy.

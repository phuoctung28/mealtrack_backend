# Hydration API

**Base prefix:** `/v1/hydration`  
**Auth:** All endpoints require `Authorization: Bearer <firebase-token>`

---

## Data Models

### `Drink` (catalog item)

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Unique drink identifier |
| `name` | `string` | Display name |
| `sub` | `string \| null` | Subtitle / variant (null for Water, Tea, Coffee, Sparkling) |
| `emoji` | `string` | Display emoji |
| `default_ml` | `int` | Suggested serving size |
| `kcal_per_100ml` | `float` | Calories per 100 ml |
| `sugar_per_100ml` | `float` | Sugar (g) per 100 ml |
| `hydration_weight` | `float` | Hydration credit multiplier (0–1) |
| `brand_color` | `string` | Hex color for UI |
| `category` | `"hydration" \| "caloric"` | Determines which log endpoint to use — **not** kcal |


```json
{
  "id": "milk-tea",
  "name": "Milk tea",
  "sub": "Boba",
  "emoji": "🧋",
  "default_ml": 500,
  "kcal_per_100ml": 76.0,
  "sugar_per_100ml": 9.0,
  "hydration_weight": 0.70,
  "brand_color": "#A87C5F",
  "category": "caloric"
}
```

---

### `HydrationEntry` (log item)

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string (uuid)` | Entry ID |
| `drink_id` | `string` | Catalog drink ID |
| `drink_name` | `string` | Resolved drink name |
| `emoji` | `string` | Drink emoji |
| `volume_ml` | `int` | Volume logged by user |
| `credited_ml` | `int` | `volume_ml × hydration_weight` |
| `kcal` | `float` | Calories for this serving |
| `source` | `"hydration"` | Current handlers use one source value for both categories |
| `meal_id` | `string (uuid)` | Compatibility ID: linked legacy meal for `/log`, hydration entry ID for `/log/drink` |
| `logged_at` | `string (ISO 8601 UTC)` | Timestamp |

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "drink_id": "water",
  "drink_name": "Water",
  "emoji": "💧",
  "volume_ml": 300,
  "credited_ml": 300,
  "kcal": 0.0,
  "source": "hydration",
  "meal_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "logged_at": "2026-05-23T08:00:00Z"
}
```

---

## Endpoints

### `GET /v1/hydration/catalog`

Returns all visible drinks in the catalog. No body, no query params.

The backing catalog currently has 13 visible drinks plus a virtual `scanned` beverage alias used by AI-scanned beverage flows. `GET /catalog` returns the 13 visible items; the virtual alias is internal only.

---

### `POST /v1/hydration/log`

Log a hydration-category drink (Water, Tea, Coffee, etc.). This compatibility
path persists both a legacy hydration meal and a normalized
`hydration_entries` row in one transaction.

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <firebase-token>` |
| `X-Timezone` | No | IANA timezone string, e.g. `Asia/Ho_Chi_Minh`. Used to resolve "today" when `target_date` is omitted. |

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `drink_id` | `string` | Yes | Must be a catalog drink with `category = "hydration"` |
| `volume_ml` | `int` | Yes | 1–2000 |
| `target_date` | `string` | No | `YYYY-MM-DD`. Defaults to user's today in their timezone. |

```json
{
  "drink_id": "water",
  "volume_ml": 300,
  "target_date": "2026-05-23"
}
```

**Response 201** — `HydrationEntry`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "drink_id": "water",
  "drink_name": "Water",
  "emoji": "💧",
  "volume_ml": 300,
  "credited_ml": 300,
  "kcal": 0.0,
  "calories": 0.0,
  "source": "hydration",
  "meal_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "logged_at": "2026-05-23T08:00:00Z"
}
```

---

### `POST /v1/hydration/log/drink`

Log a caloric drink (Milk tea, Coke, etc.). This path persists a normalized
`hydration_entries` row; it does not create a meal.

**Headers** — same as `POST /log`

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `drink_id` | `string` | Yes | Must be a catalog drink with `category = "caloric"` |
| `volume_ml` | `int` | Yes | 1–2000 |
| `target_date` | `string` | No | `YYYY-MM-DD`. Defaults to user's today. |

```json
{
  "drink_id": "milk-tea",
  "volume_ml": 500,
  "target_date": "2026-05-23"
}
```

**Response 201** — `HydrationEntry`. For backward compatibility, `meal_id`
contains the hydration entry ID.

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "meal_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "drink_id": "milk-tea",
  "drink_name": "Milk tea",
  "emoji": "🧋",
  "volume_ml": 500,
  "credited_ml": 350,
  "kcal": 379.8,
  "calories": 379.8,
  "source": "hydration",
  "logged_at": "2026-05-23T08:00:00Z"
}
```

> **Macro derivation:** the handler derives per-100 ml fat and carbs from the
> catalog values, scales and rounds the macros for the requested volume, then
> derives response calories from those rounded macros.

---

### `GET /v1/hydration/daily`

Get the daily hydration summary, entry list, and streak for a given date.

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <firebase-token>` |
| `X-Timezone` | No | IANA timezone string. Used to resolve "today". |

**Query params**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `date` | `string` | No | `YYYY-MM-DD`. Defaults to user's today. |

> `consumed_ml` = sum of `credited_ml` across all non-deleted entries for the date.  
> `percentage` = `consumed_ml / goal_ml × 100`, rounded to 1 decimal and not capped in the response.
> `goal_ml` = `daily_water_goal_ml` when present, otherwise `35 ml × body weight` rounded to the nearest integer; missing-profile and lookup-error fallback is 2000 ml.
> `streak` = consecutive days ending on or before today where `consumed_ml >= goal_ml`, computed from the merged normalized + legacy 31-day history window.

---

### `GET /v1/hydration/weekly`

Get 7-day hydration chart data for a calendar week.

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <firebase-token>` |
| `X-Timezone` | No | IANA timezone string. Used to resolve current week. |

**Query params**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `start_date` | `string` | No | `YYYY-MM-DD` — Monday of the desired week. Defaults to current week's Monday in user's timezone. |

> Days with no entries return `consumed_ml: 0`. Always 7 days Mon–Sun.

---

### `DELETE /v1/hydration/{entry_id}`

Soft-delete a hydration entry. If the normalized entry references a legacy
hydration meal, that meal is also deactivated.

**Path param**

| Param | Type | Description |
|-------|------|-------------|
| `entry_id` | `string (uuid)` | ID of the hydration entry to delete |

**Response 200**

```json
{ "success": true }
```

---

## Drink Catalog

13 visible drinks total (5 hydration, 8 caloric) plus one internal `scanned` alias.

| `id` | Name | Category | Default | kcal/100ml | hydration_weight | `sub` |
|------|------|----------|---------|------------|-----------------|-------|
| `water` | Water | hydration | 250 ml | 0 | 1.00 | null |
| `sparkling` | Sparkling | hydration | 250 ml | 0 | 1.00 | "Carbonated" |
| `tea` | Tea | hydration | 250 ml | 1 | 0.90 | null |
| `coffee` | Coffee | hydration | 250 ml | 1 | 0.80 | null |
| `coke-zero` | Coke Zero | hydration | 330 ml | 0 | 1.00 | "No sugar" |
| `electrolyte` | Electrolyte | caloric | 500 ml | 2 | 0.95 | "Sports drink" |
| `milk-tea` | Milk tea | caloric | 500 ml | 76 | 0.70 | "Boba" |
| `coke` | Soda | caloric | 330 ml | 42.1 | 0.80 | "Soft drink" |
| `oj` | Fruit juice | caloric | 250 ml | 44 | 0.95 | "Fresh pressed" |
| `smoothie` | Smoothie | caloric | 400 ml | 62.5 | 0.90 | "Açaí blend" |
| `energy` | Energy drink | caloric | 250 ml | 44 | 0.85 | "Red Bull" |
| `iced-latte` | Iced latte | caloric | 350 ml | 37.1 | 0.85 | "Cold brew" |
| `beer` | Beer | caloric | 330 ml | 45.5 | 0.60 | "Lager" |

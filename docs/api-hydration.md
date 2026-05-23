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

> **Note on `coke-zero`:** It has `category: "caloric"` even though `kcal_per_100ml = 0`. Use `category`, not `kcal`, to decide which endpoint to call. This is intentional — category determines log behavior.

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
| `source` | `"hydration" \| "caloric_drink"` | Log source |
| `meal_id` | `string (uuid) \| null` | Linked meal ID (caloric only) |
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
  "meal_id": null,
  "logged_at": "2026-05-23T08:00:00Z"
}
```

---

## Endpoints

### `GET /v1/hydration/catalog`

Returns all drinks in the catalog. No body, no query params.

**Response 200**

```json
{
  "drinks": [
    {
      "id": "water",
      "name": "Water",
      "sub": null,
      "emoji": "💧",
      "default_ml": 250,
      "kcal_per_100ml": 0.0,
      "sugar_per_100ml": 0.0,
      "hydration_weight": 1.0,
      "brand_color": "#3B82F6",
      "category": "hydration"
    }
    // ... 12 more
  ]
}
```

---

### `POST /v1/hydration/log`

Log a zero-calorie or hydration drink (Water, Tea, Coffee, etc.).

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
  "source": "hydration",
  "meal_id": null,
  "logged_at": "2026-05-23T08:00:00Z"
}
```

---

### `POST /v1/hydration/log/drink`

Log a caloric drink (Milk tea, Coke, etc.). Creates a **hydration entry** and a **meal entry** atomically in a single transaction.

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

**Response 201** — `HydrationEntry` with `meal_id` populated

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "meal_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "drink_id": "milk-tea",
  "drink_name": "Milk tea",
  "emoji": "🧋",
  "volume_ml": 500,
  "credited_ml": 350,
  "kcal": 380.0,
  "source": "caloric_drink",
  "logged_at": "2026-05-23T08:00:00Z"
}
```

> **Macro derivation:** `carbs = sugar_per_100ml × (volume_ml / 100)`, `fat = max(0, (kcal - sugar×4) / 9) × (volume_ml / 100)`, `protein = 0`. Calories are never stored — always derived.

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

**Response 200**

```json
{
  "date": "2026-05-23",
  "consumed_ml": 1250,
  "goal_ml": 2000,
  "percentage": 62.5,
  "streak": 5,
  "entries": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "drink_id": "water",
      "drink_name": "Water",
      "emoji": "💧",
      "volume_ml": 300,
      "credited_ml": 300,
      "kcal": 0.0,
      "source": "hydration",
      "meal_id": null,
      "logged_at": "2026-05-23T08:00:00Z"
    }
  ]
}
```

> `consumed_ml` = sum of `credited_ml` across all non-deleted entries for the date.  
> `percentage` = `consumed_ml / goal_ml × 100`, capped at 100.  
> `goal_ml` = per-user setting, defaults to `2000` until configurable via profile update.  
> `streak` = consecutive days where `consumed_ml >= goal_ml`, ending on or before today. Resets to `0` if the last qualifying day is before yesterday.

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

**Response 200**

```json
{
  "week_start": "2026-05-19",
  "goal_ml": 2000,
  "days": [
    { "date": "2026-05-19", "consumed_ml": 1800 },
    { "date": "2026-05-20", "consumed_ml": 2100 },
    { "date": "2026-05-21", "consumed_ml": 950 },
    { "date": "2026-05-22", "consumed_ml": 2000 },
    { "date": "2026-05-23", "consumed_ml": 750 },
    { "date": "2026-05-24", "consumed_ml": 0 },
    { "date": "2026-05-25", "consumed_ml": 0 }
  ]
}
```

> Days with no entries return `consumed_ml: 0`. Always 7 days Mon–Sun.

---

### `DELETE /v1/hydration/{entry_id}`

Soft-delete a hydration entry. If the entry has a linked meal (`source = "caloric_drink"`), that meal is also deactivated.

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

| `id` | Name | Category | Default | kcal/100ml | `sub` |
|------|------|----------|---------|------------|-------|
| `water` | Water | hydration | 250 ml | 0 | null |
| `sparkling` | Sparkling water | hydration | 250 ml | 0 | null |
| `tea` | Tea | hydration | 250 ml | 0 | null |
| `coffee` | Coffee | hydration | 250 ml | 0 | null |
| `electrolyte` | Electrolyte | hydration | 500 ml | 2 | "Sports drink" |
| `milk-tea` | Milk tea | caloric | 500 ml | 76 | "Boba" |
| `coke` | Coca-Cola | caloric | 330 ml | 42.1 | "Regular" |
| `coke-zero` | Coke Zero | caloric | 330 ml | 0 | "Diet" |
| `oj` | Orange juice | caloric | 250 ml | 44 | "Fresh" |
| `iced-latte` | Iced latte | caloric | 350 ml | 37.1 | "Café · milk" |
| `smoothie` | Smoothie | caloric | 400 ml | 62.5 | "Açaí blend" |
| `energy` | Energy drink | caloric | 250 ml | 44 | "Red Bull" |
| `beer` | Beer | caloric | 330 ml | 45.5 | "Lager · 5%" |

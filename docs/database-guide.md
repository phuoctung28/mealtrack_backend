# Backend Database Guide

**Last Updated:** June 9, 2026
**Engine:** PostgreSQL (Neon) + SQLAlchemy 2.0 (psycopg2 sync / asyncpg async)
**Migrations:** Alembic with auto-migration on startup
**Tables:** 30+ (core tables + normalized profile/hydration/recipe/food/referral tables)

---

## Standards Gate

Before creating or changing tables, read and follow
[`docs/standards/db-api.md`](./standards/db-api.md).

Non-negotiable database rules:

- OLTP source-of-truth tables follow 3NF unless a documented exception exists.
- User-owned tables use `ForeignKey("users.id")` unless retention/legal rules require otherwise.
- JSON must not be the permanent owner of business entities, user preferences, workflow state, or queryable product data.
- Schema migrations use expand-migrate-contract for existing data: add normalized structure, backfill, dual-write/read fallback, cut over, then remove legacy columns later.
- New ORM models must be imported by the central model registry so Alembic sees them.

---

## Connection Configuration

```python
# src/infra/database/config.py
DATABASE_URL = "postgresql+psycopg2://user:pass@host/db"

pool_size = 20       # Base connections
max_overflow = 10    # Additional under load
pool_recycle = 3600  # Recycle hourly
pool_pre_ping = True # Verify before use
```

---

## Core Tables

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **users** | Auth & identity | id, firebase_uid, email, language_code, is_active |
| **user_profiles** | Health metrics | user_id, age, gender, height, weight, body_fat_percentage, date_of_birth |
| **user_profile_preferences** | Normalized profile arrays | profile_id, preference_type, value, position |
| **subscriptions** | RevenueCat cache | user_id, product_id, platform, status, expires_at |
| **meal** | Meal records | meal_id, user_id, status (state machine), dish_name, ready_at |
| **mealimage** | Cloudinary refs | image_id, url, format, size_bytes, width, height |
| **nutrition** | Meal macro facts | meal_id, protein, carbs, fat, fiber, sugar, confidence_score |
| **food_item** | Ingredients | nutrition_id, name, quantity, unit, fdc_id, food_reference_id, is_custom, fiber, sugar |
| **food_reference** | Barcode/food data | barcode, name, name_normalized, nutrition data |
| **food_reference_serving_sizes** | Normalized serving conversions | food_reference_id, name, grams, milliliters, is_default, position |
| **food_reference_nutrients** | Normalized extended nutrients | food_reference_id, nutrient_key, amount, unit |
| **hydration_entries** | Normalized hydration logs | user_id, drink_id, volume_ml, credited_ml, macro facts, logged_at, legacy_meal_id |
| **meal_instruction_steps** | Normalized recipe steps | meal_id, instruction, duration_minutes, position |
| **user_fcm_tokens** | Push tokens | user_id, fcm_token, device_type, is_active |
| **notification_preferences** | FCM settings | user_id, reminder flags, timing, language, is_deleted |
| **notifications** | Prebuilt notification queue | user_id, notification_type, scheduled_date, scheduled_for_utc, context snapshot |
| **saved_suggestions** | Saved meal suggestion headers | user_id, suggestion_id, meal_type, suggestion_data compatibility snapshot |
| **saved_suggestion_items** | Saved suggestion ingredients | saved_suggestion_id, name, quantity, unit, macro facts, position |
| **saved_suggestion_steps** | Saved suggestion recipe steps | saved_suggestion_id, instruction, duration_minutes, position |
| **weekly_macro_budgets** | Weekly target/consumed facts | user_id, week_start_date, target macros, consumed macros |
| **cheat_days** | User cheat day markers | user_id, date, marked_at |
| **weight_entries** | Weight history | user_id, weight_kg, recorded_at |
| **movement_entries** | Movement logs | user_id, activity_name, duration_min, kcal_burned, logged_at |
| **referral_codes** | Referral code ownership | user_id, code, created_at |
| **referral_conversions** | Referral conversion audit | referrer_user_id, referred_user_id, status, commission fields |
| **referral_wallets** | Referral wallet totals | user_id, balance, total_earned, total_withdrawn |
| **payout_requests** | Referral payout workflow | user_id, amount, payment_method, typed masked destination, payment_details snapshot, status |

---

## Model Mixins

Three base mixins in `src/infra/database/models/base.py`:

| Mixin | ID Type | Use Case |
|-------|---------|---------|
| `PrimaryEntityMixin` | GUID String(36) | Top-level aggregates (Meal, User) |
| `SecondaryEntityMixin` | Auto-increment int | Child entities (Nutrition, FoodItem) |
| `TimestampMixin` | No ID | Join tables or log tables |

All mixins add `created_at` and `updated_at` timestamps.

---

## Relationships

```
User (1:N) UserProfile, Subscription, Meal, NotificationPreferences, UserFcmToken, HydrationEntry
UserProfile (1:N) UserProfilePreference
Meal (1:1) MealImage, Nutrition
Meal (1:N) MealInstructionStep
Nutrition (1:N) FoodItem
SavedSuggestion (1:N) SavedSuggestionItem, SavedSuggestionStep
FoodReference (1:N) FoodReferenceServingSize, FoodReferenceNutrient
```

---

## Meal Status State Machine

```
PROCESSING → ANALYZING → ENRICHING → READY
                                    ↓
                                  FAILED
                                    ↓
                                 INACTIVE
```

---

## Migrations

```bash
alembic upgrade head                              # Apply latest
alembic revision --autogenerate -m "description"  # Create new
alembic downgrade -1                              # Rollback one
```

Auto-migrate runs on startup with retry logic. Use timestamp naming for new migrations.

**Recent migrations:**

| Version | Changes |
|---------|---------|
| 20260609000006 | Add normalized read-path indexes for active FCM tokens, notification reschedule/delete, and stale processing reclaim |
| 20260609000005 | Add normalized food serving/nutrient tables, payout typed workflow fields, notification context schema version |
| 20260609000004 | Add normalized saved suggestion ingredients/steps and meal recipe instruction steps |
| 20260609000003 | Add normalized hydration_entries and backfill from legacy hydration meals |
| 20260609000002 | Add normalized user_profile_preferences and backfill profile JSON arrays |
| 20260609000001 | Add/align user ownership FKs for private user-owned tables |
| 047 | Add notification_sent_log for FCM deduplication |
| 046 | Add name_normalized to food_reference |
| 045 | Add challenge_duration, training_types (onboarding) |
| 044 | Widen firebase_uid to 128 chars |
| 043 | Add language_code to users |
| 037 | Add custom_protein_g, custom_carbs_g, custom_fat_g |
| 035 | Evolve barcode_products → food_reference |
| 034 | Add fiber, sugar to food_item and nutrition |

**Temporary compatibility fields:** `user_profiles` keeps legacy JSON array columns during read fallback, `saved_suggestions.suggestion_data` remains a raw compatibility snapshot, `meal.instructions` remains a recipe-step compatibility snapshot, `food_reference.serving_sizes` and `food_reference.extra_nutrients` remain legacy response snapshots, `payout_requests.payment_details` remains raw sensitive payout detail pending a security/contract pass, and legacy hydration meal rows remain readable during rollout. `notifications.context` is an immutable render snapshot only; recipient truth lives in `user_fcm_tokens`. Do not add new source-of-truth JSON fields without a documented exception in `docs/standards/db-api.md`.

**Production migration rule:** production schema creation is Alembic-only. `migrations/run.py` upgrades empty databases from base to head and refuses to stamp an existing unversioned schema automatically.

---

## Repository Pattern

**Smart Sync:** Update existing or insert new record, with diff-based updates for nested entities.

**Eager Loading:** Pre-defined `joinedload` options per repository — avoids N+1 queries consistently.

**Session Scope:** Request-scoped sessions via FastAPI dependency injection. One session per request, never shared across requests.

---

## Performance Optimization

- Indexes on `firebase_uid`, `status`, date columns, and `user_id` foreign keys
- `joinedload` / `selectinload` for known relationship paths
- Connection pool: 20 base + 10 overflow, recycled hourly
- Redis cache-aside for frequently read data (see `external-services.md`)

---

See related: `system-architecture.md`, `external-services.md`, `code-standards.md`, `standards/db-api.md`

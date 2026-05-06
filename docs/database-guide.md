# Backend Database Guide

**Last Updated:** May 6, 2026
**Engine:** MySQL 8.0 + SQLAlchemy 2.0
**Migrations:** Alembic with auto-migration on startup
**Tables:** 15 (13 core + notification_sent_log + food_reference)

---

## Connection Configuration

```python
# src/infra/database/config.py
DATABASE_URL = "mysql+pymysql://user:pass@host/db"

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
| **subscriptions** | RevenueCat cache | user_id, product_id, platform, status, expires_at |
| **meal** | Meal records | id, user_id, status (state machine), dish_name, ready_at |
| **meal_image** | Cloudinary refs | meal_id, url, format, size, width, height |
| **nutrition** | Macros | meal_id, calories, protein, carbs, fat, fiber, sugar, confidence_score |
| **food_item** | Ingredients | meal_id, name, quantity, unit, fdc_id, is_custom, fiber, sugar |
| **food_reference** | Barcode/food data | barcode, name, name_normalized, nutrition data |
| **meal_plan** | Weekly plans | user_id, start_date, end_date, user_preferences |
| **meal_plan_day** | Daily breakdown | meal_plan_id, day_index |
| **planned_meal** | Individual meals | day_plan_id, meal_type, dish_name, nutrition |
| **user_fcm_tokens** | Push tokens | user_id, token, platform (ios/android), device_id |
| **notification_preferences** | FCM settings | user_id, enabled, timing, interval |
| **chat_threads** | Conversations | id, user_id, title, status, created_at |
| **chat_messages** | Messages | thread_id, user_id, role (user/assistant), content, created_at |
| **notification_sent_log** | FCM dedup | user_id, notification_type, sent_minute, created_at |

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
User (1:N) UserProfile, Subscription, Meal, NotificationPreferences, UserFcmToken
Meal (1:1) MealImage, Nutrition
Nutrition (1:N) FoodItem
MealPlan (1:N) MealPlanDay (1:N) PlannedMeal
ChatThread (1:N) ChatMessage
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
| 047 | Add notification_sent_log for FCM deduplication |
| 046 | Add name_normalized to food_reference |
| 045 | Add challenge_duration, training_types (onboarding) |
| 044 | Widen firebase_uid to 128 chars |
| 043 | Add language_code to users |
| 037 | Add custom_protein_g, custom_carbs_g, custom_fat_g |
| 035 | Evolve barcode_products → food_reference |
| 034 | Add fiber, sugar to food_item and nutrition |

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

See related: `system-architecture.md`, `external-services.md`, `code-standards.md`

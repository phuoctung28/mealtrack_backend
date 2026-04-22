# Backend Database Guide

**Last Updated:** April 17, 2026  
**Engine:** MySQL 8.0 + SQLAlchemy 2.0  
**Migrations:** Alembic with auto-migration on startup  
**Tables:** 13+ core + notification_sent_log (dedup)

---

## Connection Configuration

```python
# src/infra/database/config.py
DATABASE_URL = "mysql+pymysql://user:pass@host/db"

# Pool sizing
pool_size = 20           # Base connections
max_overflow = 10        # Additional under load
pool_recycle = 3600      # Recycle connections hourly
pool_pre_ping = True     # Verify before use
```

---

## Core Tables

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **users** | Auth & identity | id, firebase_uid, email, is_active |
| **user_profiles** | Health metrics | user_id, age, gender, height, weight, body_fat_percentage |
| **subscriptions** | RevenueCat cache | user_id, product_id, platform, status, expires_at |
| **meal** | Meal records | id, user_id, status (state machine), dish_name, ready_at |
| **meal_image** | Cloudinary refs | meal_id, url, format, size, width, height |
| **nutrition** | Macros | meal_id, calories, protein, carbs, fat, fiber, sugar, confidence_score |
| **food_item** | Ingredients | meal_id, name, quantity, unit, fdc_id, is_custom, fiber, sugar |
| **meal_plan** | Weekly plans | user_id, start_date, end_date, user_preferences |
| **meal_plan_day** | Daily breakdown | meal_plan_id, day_index |
| **planned_meal** | Individual meals | day_plan_id, meal_type, dish_name, nutrition |
| **user_fcm_tokens** | Push tokens | user_id, token, platform (ios/android), device_id |
| **notification_preferences** | FCM settings | user_id, enabled, timing, interval |
| **chat_threads** | Conversations | id, user_id, title, status, created_at |
| **chat_messages** | Messages | thread_id, user_id, role (user/assistant), content, created_at |
| **notification_sent_log** | Dedup (047) | user_id, notification_type, sent_minute, created_at |

---

## Model Mixins

```python
# src/infra/database/models/base.py

class PrimaryEntityMixin:
    """GUID primary key (String(36)), timestamps"""
    id: str = Column(String(36), primary_key=True)
    created_at: datetime = Column(DateTime, default=utcnow)
    updated_at: datetime = Column(DateTime, onupdate=utcnow)

class SecondaryEntityMixin:
    """Auto-increment integer ID, timestamps"""
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    created_at: datetime = Column(DateTime, default=utcnow)
    updated_at: datetime = Column(DateTime, onupdate=utcnow)

class TimestampMixin:
    """Only timestamps (no ID)"""
    created_at: datetime = Column(DateTime, default=utcnow)
    updated_at: datetime = Column(DateTime, onupdate=utcnow)
```

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

Managed via Alembic. Auto-migrate on startup with retry logic.

**Run migrations:**
```bash
# Apply latest
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback one
alembic downgrade -1
```

**Recent migrations:**
| Version | Changes | Date |
|---------|---------|------|
| 047 | Add notification_sent_log for dedup | Apr 2026 |
| 046 | Add name_normalized to food_reference | Apr 2026 |
| 045 | Add challenge_duration, training_types (onboarding) | Apr 2026 |
| 044 | Widen firebase_uid to 128 chars | Mar 2026 |
| 043 | Add language_code to users | Mar 2026 |
| 037 | Add custom_protein_g, custom_carbs_g, custom_fat_g | Mar 2026 |
| 036 | Add date_of_birth to user_profiles | Mar 2026 |
| 035 | Evolve barcode_products → food_reference | Mar 2026 |
| 034 | Add fiber, sugar to food_item, nutrition | Mar 2026 |

---

## Repository Pattern

**Smart Sync:** Update existing or create new
```python
def save(self, meal: Meal) -> Meal:
    # If meal.id exists: update record
    # If meal.id is new: insert record
    # Handle nested entities (food items) with diff-based updates
    pass
```

**Eager Loading:** Pre-defined options for consistent performance
```python
_load_options = [
    joinedload(MealModel.image),
    joinedload(MealModel.nutrition).joinedload(Nutrition.food_items),
]

def find_by_id(self, meal_id: str) -> Optional[Meal]:
    db_meal = self.session.query(MealModel).options(
        *self._load_options
    ).filter_by(meal_id=meal_id).first()
    return db_meal.to_domain() if db_meal else None
```

---

## Domain ↔ DB Mapping

```python
class Meal(PrimaryEntityMixin, Base):
    __tablename__ = "meal"
    
    # DB relationships with eager loading
    image = relationship("MealImage", lazy="joined")
    nutrition = relationship("Nutrition", lazy="joined")
    
    # Convert to domain
    def to_domain(self) -> DomainMeal:
        return DomainMeal(...)
    
    # Convert from domain
    @staticmethod
    def from_domain(meal: DomainMeal) -> "Meal":
        return Meal(...)
```

---

## Session Management

Request-scoped sessions via ContextVar (singleton-safe):

```python
# src/infra/database/config.py
async_session = AsyncSessionLocal()

# Request-scoped
@app.middleware("http")
async def add_session(request, call_next):
    async with async_session() as session:
        # Inject into request
        request.state.session = session
        return await call_next(request)
```

---

## Performance Optimization

- **Eager Loading:** Pre-defined load options for known relationships
- **Connection Pooling:** 20 base + 10 overflow, recycled hourly
- **Indexes:** Firebase UID, status, dates, user_id foreign keys
- **Queries:** Avoid N+1 with joinedload and selectinload
- **Sessions:** Request-scoped (fresh per request, no global state)

---

See related: `system-architecture.md`, `external-services.md`, `code-standards.md`

"""
Meal, nutrition, weekly budget, and cheat day DB inserts for demo seed.

Calories are always derived from macros: P*4 + (C-fiber)*4 + fiber*2 + F*9
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.infra.database.models.meal.meal import MealORM
from src.infra.database.models.meal.meal_image import MealImageORM
from src.infra.database.models.nutrition.nutrition import NutritionORM
from src.infra.database.models.nutrition.food_item import FoodItemORM
from src.infra.database.models.weekly.weekly_macro_budget import WeeklyMacroBudget
from src.infra.database.models.cheat_day.cheat_day import CheatDay
from src.infra.database.models.enums import MealStatusEnum

from scripts.seed_demo_meals import ALL_DAYS_MEALS, CHEAT_DAY_INDICES

# Daily macro targets — profile: 28yo male, 175cm, 70kg, desk+4d training, cut
# TDEE ≈ 2,317 kcal → 500 kcal deficit → derived from P=154 C=174 F=56
DAILY_TARGET_CALORIES = 1844.0
DAILY_TARGET_PROTEIN = 154.0
DAILY_TARGET_CARBS = 174.0
DAILY_TARGET_FAT = 56.0

PLACEHOLDER_IMAGE_URL = (
    "https://res.cloudinary.com/demo/image/upload/v1/nutree/placeholder_meal.jpg"
)
MEAL_HOURS = {"breakfast": 7, "lunch": 12, "dinner": 19, "snack": 16}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _meal_datetime(day_offset: int, hour: int) -> datetime:
    d = _week_start() + timedelta(days=day_offset)
    return datetime(d.year, d.month, d.day, hour, 0, 0, tzinfo=timezone.utc)


def _derive_calories(protein: float, carbs: float, fat: float, fiber: float = 0.0) -> float:
    """Fiber-aware calorie derivation: P*4 + (C-fiber)*4 + fiber*2 + F*9"""
    return round(protein * 4 + max(0.0, carbs - fiber) * 4 + fiber * 2 + fat * 9, 1)


def seed_meals(db: Session, user_id: str) -> None:
    """Insert 6 days of meals with nutrition and food items."""
    for day_idx, day_meals in enumerate(ALL_DAYS_MEALS):
        for meal_data in day_meals:
            meal_id = str(uuid.uuid4())
            image_id = str(uuid.uuid4())
            ts = _meal_datetime(day_idx, MEAL_HOURS.get(meal_data.meal_type, 12))

            db.add(MealImageORM(
                image_id=image_id,
                format="jpeg",
                size_bytes=102400,
                width=800,
                height=600,
                url=PLACEHOLDER_IMAGE_URL,
                created_at=ts,
                updated_at=ts,
            ))
            db.add(MealORM(
                meal_id=meal_id,
                user_id=user_id,
                status=MealStatusEnum.READY,
                dish_name=meal_data.dish_name,
                meal_type=meal_data.meal_type,
                source=meal_data.source,
                image_id=image_id,
                ready_at=ts,
                created_at=ts,
                updated_at=ts,
                edit_count=0,
                is_manually_edited=False,
            ))

            nutrition = NutritionORM(
                meal_id=meal_id,
                protein=meal_data.total_protein(),
                carbs=meal_data.total_carbs(),
                fat=meal_data.total_fat(),
                fiber=meal_data.total_fiber(),
                sugar=meal_data.total_sugar(),
                confidence_score=0.92,
                created_at=ts,
                updated_at=ts,
            )
            db.add(nutrition)
            db.flush()  # materialise nutrition.id before food_item FK

            for item in meal_data.food_items:
                db.add(FoodItemORM(
                    id=str(uuid.uuid4()),
                    name=item.name,
                    quantity=item.quantity,
                    unit=item.unit,
                    protein=item.protein,
                    carbs=item.carbs,
                    fat=item.fat,
                    fiber=item.fiber,
                    sugar=item.sugar,
                    nutrition_id=nutrition.id,
                    confidence=0.90,
                    is_custom=False,
                    is_deleted=False,
                    created_at=ts,
                    updated_at=ts,
                ))


def seed_weekly_budget(db: Session, user_id: str) -> None:
    """Insert weekly budget reflecting all logged meals as consumed totals."""
    consumed_protein = sum(m.total_protein() for d in ALL_DAYS_MEALS for m in d)
    consumed_carbs = sum(m.total_carbs() for d in ALL_DAYS_MEALS for m in d)
    consumed_fat = sum(m.total_fat() for d in ALL_DAYS_MEALS for m in d)
    consumed_fiber = sum(m.total_fiber() for d in ALL_DAYS_MEALS for m in d)
    consumed_calories = _derive_calories(
        consumed_protein, consumed_carbs, consumed_fat, consumed_fiber
    )
    db.add(WeeklyMacroBudget(
        weekly_budget_id=str(uuid.uuid4()),
        user_id=user_id,
        week_start_date=_week_start(),
        target_calories=round(DAILY_TARGET_CALORIES * 7, 1),
        target_protein=round(DAILY_TARGET_PROTEIN * 7, 1),
        target_carbs=round(DAILY_TARGET_CARBS * 7, 1),
        target_fat=round(DAILY_TARGET_FAT * 7, 1),
        consumed_calories=round(consumed_calories, 1),
        consumed_protein=round(consumed_protein, 1),
        consumed_carbs=round(consumed_carbs, 1),
        consumed_fat=round(consumed_fat, 1),
        created_at=_utc_now(),
        updated_at=_utc_now(),
    ))


def seed_cheat_days(db: Session, user_id: str) -> None:
    """Flag cheat days defined in CHEAT_DAY_INDICES."""
    monday = _week_start()
    for day_idx in CHEAT_DAY_INDICES:
        cheat_date = monday + timedelta(days=day_idx)
        db.add(CheatDay(
            id=str(uuid.uuid4()),
            user_id=user_id,
            date=cheat_date,
            marked_at=datetime(
                cheat_date.year, cheat_date.month, cheat_date.day, 21, 0, 0,
                tzinfo=timezone.utc,
            ),
        ))

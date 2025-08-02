"""
Command handler for weekly ingredient-based meal-plan generation.
Works with Python 3.11 and the simplified WeeklyIngredientBasedMealPlanService.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.app.commands.meal_plan import GenerateWeeklyIngredientBasedMealPlanCommand
from src.app.events.base import EventHandler, handles
from src.app.handlers.command_handlers.user_command_handlers import (
    SaveUserOnboardingCommandHandler,
)
from src.domain.model.meal_plan import (
    DayPlan,
    DietaryPreference,
    FitnessGoal,
    MealPlan,
    MealType,
    PlanDuration,
    PlannedMeal,
    UserPreferences,
)
from src.infra.database.models.meal_planning import (
    MealPlan as MealPlanORM,
    MealPlanDay as MealPlanDayORM,
    PlannedMeal as PlannedMealORM,
)
from src.infra.database.models.enums import (
    FitnessGoalEnum,
    PlanDurationEnum,
    MealTypeEnum,
)
from src.domain.services.weekly_ingredient_based_meal_plan_service import (
    WeeklyIngredientBasedMealPlanService,
)
from src.infra.database.models.user import UserProfile
from src.infra.repositories.meal_plan_repository import MealPlanRepository

logger = logging.getLogger(__name__)


@handles(GenerateWeeklyIngredientBasedMealPlanCommand)
class GenerateWeeklyIngredientBasedMealPlanCommandHandler(
    EventHandler[GenerateWeeklyIngredientBasedMealPlanCommand, Dict[str, Any]]
):
    """Generate and persist a Monday-to-Sunday meal plan."""

    def __init__(self, db: Optional[Session] = None) -> None:
        self.db: Optional[Session] = db
        self.meal_plan_service = WeeklyIngredientBasedMealPlanService()
        self.meal_plan_repository = MealPlanRepository(db) if db else None

    # ------------------------------------------------------------------ #
    # dependency injection                                               #
    # ------------------------------------------------------------------ #

    def set_dependencies(self, db: Session) -> None:
        self.db = db
        self.meal_plan_repository = MealPlanRepository(db)

    # ------------------------------------------------------------------ #
    # main handler                                                       #
    # ------------------------------------------------------------------ #

    async def handle(
        self, command: GenerateWeeklyIngredientBasedMealPlanCommand
    ) -> Dict[str, Any]:
        if not self.db:
            raise RuntimeError("Database session not configured")

        logger.info(
            "Generating weekly ingredient-based meal plan for user %s (%d ingredients)",
            command.user_id,
            len(command.available_ingredients),
        )

        # ── 1. pull user profile or fall back to defaults ───────────────
        profile: Optional[UserProfile] = (
            self.db.query(UserProfile)
            .filter(UserProfile.user_id == command.user_id, UserProfile.is_current)
            .first()
        )

        if profile:
            onboarding_handler = SaveUserOnboardingCommandHandler(self.db)
            tdee = onboarding_handler._calculate_tdee_and_macros(profile)

            dietary_prefs = profile.dietary_preferences or []
            allergies = profile.allergies or []
            target_cal = tdee["target_calories"]
            macros = tdee["macros"]
            meals_per_day = profile.meals_per_day
            include_snacks = profile.snacks_per_day > 0
            age = profile.age
            gender = profile.gender
            activity = profile.activity_level
            fitness_goal = profile.fitness_goal
        else:
            dietary_prefs: List[str] = []
            allergies: List[str] = []
            target_cal = 2_000
            macros = {"protein": 150, "carbs": 250, "fat": 70}
            meals_per_day = 3
            include_snacks = True
            age = 30
            gender = "male"
            activity = "moderate"
            fitness_goal = "maintenance"

        # ── 2. call the meal-plan service ───────────────────────────────
        request_data = {
            "user_id": command.user_id,
            "available_ingredients": command.available_ingredients,
            "available_seasonings": command.available_seasonings,
            "dietary_preferences": dietary_prefs,
            "allergies": allergies,
            "target_calories": target_cal,
            "target_protein": macros["protein"],
            "target_carbs": macros["carbs"],
            "target_fat": macros["fat"],
            "meals_per_day": meals_per_day,
            "include_snacks": include_snacks,
            "age": age,
            "gender": gender,
            "activity_level": activity,
            "fitness_goal": fitness_goal,
        }

        try:
            plan_json = self.meal_plan_service.generate_weekly_meal_plan(request_data)
        except Exception as exc:  # pragma: no cover
            logger.exception("Meal-plan generation failed")
            raise

        logger.info("Meal plan generated for user %s", command.user_id)

        # ── 3. persist if we have a profile ─────────────────────────────
        if profile and self.meal_plan_repository:
            meal_plan = self._persist_meal_plan(profile, plan_json, request_data)
            plan_json["plan_id"] = meal_plan.plan_id

        return plan_json

    # ------------------------------------------------------------------ #
    # persistence helpers                                                #
    # ------------------------------------------------------------------ #

    def _persist_meal_plan(
        self,
        profile: UserProfile,
        plan_json: Dict[str, Any],
        req: Dict[str, Any],
    ) -> MealPlan:
        """Convert JSON into domain objects and store them."""

        # ── preferences --------------------------------------------------
        valid_prefs = []
        for p in req.get("dietary_preferences", []):
            try:
                valid_prefs.append(DietaryPreference(p))
            except ValueError:
                logger.warning("Unknown dietary preference: %s – skipped", p)

        preferences = UserPreferences(
            dietary_preferences=valid_prefs,
            allergies=req.get("allergies", []),
            fitness_goal=FitnessGoal(req.get("fitness_goal", "maintenance")),
            meals_per_day=req.get("meals_per_day", 3),
            snacks_per_day=1 if req.get("include_snacks", False) else 0,
            cooking_time_weekday=30,
            cooking_time_weekend=45,
            favorite_cuisines=req.get("favorite_cuisines", []),
            disliked_ingredients=req.get("disliked_ingredients", []),
            plan_duration=PlanDuration.WEEKLY,
        )

        # ── day-plans ----------------------------------------------------
        # ── day-plans ────────────────────────────────────────────────────────
        today = datetime.now().date()
        weekday_index = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
        }

        # Create the ORM meal plan first
        # Convert domain enums to database enums
        fitness_goal_orm = FitnessGoalEnum(preferences.fitness_goal.value)
        plan_duration_orm = PlanDurationEnum(preferences.plan_duration.value)
        
        meal_plan_orm = MealPlanORM(
            user_id=profile.user_id,
            dietary_preferences=[pref.value for pref in preferences.dietary_preferences],
            allergies=preferences.allergies,
            fitness_goal=fitness_goal_orm,
            meals_per_day=preferences.meals_per_day,
            snacks_per_day=preferences.snacks_per_day,
            cooking_time_weekday=preferences.cooking_time_weekday,
            cooking_time_weekend=preferences.cooking_time_weekend,
            favorite_cuisines=preferences.favorite_cuisines,
            disliked_ingredients=preferences.disliked_ingredients,
            plan_duration=plan_duration_orm,
        )
        self.db.add(meal_plan_orm)
        self.db.flush()  # Get the meal plan ID

        day_plans: List[DayPlan] = []

        for day_name, meals_json in plan_json["days"].items():
            offset = weekday_index[day_name.lower()]
            day_date = today + timedelta(days=offset)

            # 1) Create ORM MealPlanDay
            day_plan_orm = MealPlanDayORM(
                meal_plan_id=meal_plan_orm.id,
                date=day_date
            )
            self.db.add(day_plan_orm)
            self.db.flush()  # Get the day plan ID

            # 2) Create ORM PlannedMeal objects
            planned_meals: List[PlannedMeal] = []
            for m_json in meals_json:
                meal_data = self._to_meal_dict(m_json)
                meal_orm = PlannedMealORM(
                    day_id=day_plan_orm.id,
                    **meal_data
                )
                self.db.add(meal_orm)
                
                # Create domain model for return response
                domain_meal = self._to_domain_meal(m_json)
                planned_meals.append(domain_meal)

            # Create domain DayPlan for return response
            day_plan = DayPlan(date=day_date, meals=planned_meals)
            day_plans.append(day_plan)

        # ── assemble domain model for return ---------------------------------------------
        try:
            meal_plan = MealPlan(user_id=profile.user_id, preferences=preferences, days=day_plans)
            meal_plan.plan_id = meal_plan_orm.id  # Use the ORM ID
            
            self.db.commit()  # Commit all changes
            return meal_plan
        except Exception as e:
            self.db.rollback()  # Rollback on error
            logger.exception("Failed to persist meal plan")
            raise

    @staticmethod
    def _to_meal_dict(meal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert meal JSON to dict for ORM PlannedMeal creation."""
        try:
            meal_type = MealTypeEnum(meal_data["meal_type"].lower())
        except (KeyError, ValueError):
            logger.warning("Unknown or missing meal_type – defaulting to breakfast")
            meal_type = MealTypeEnum.breakfast

        return {
            "meal_type": meal_type,
            "name": meal_data.get("name", "Unnamed meal"),
            "description": meal_data.get("description", ""),
            "prep_time": meal_data.get("prep_time", 0),
            "cook_time": meal_data.get("cook_time", 0),
            "calories": meal_data.get("calories", 0),
            "protein": meal_data.get("protein", 0.0),
            "carbs": meal_data.get("carbs", 0.0),
            "fat": meal_data.get("fat", 0.0),
            "ingredients": meal_data.get("ingredients", []),
            "instructions": meal_data.get("instructions", []),
            "is_vegetarian": meal_data.get("is_vegetarian", False),
            "is_vegan": meal_data.get("is_vegan", False),
            "is_gluten_free": meal_data.get("is_gluten_free", False),
            "cuisine_type": meal_data.get("cuisine_type", "International"),
        }

    @staticmethod
    def _to_domain_meal(meal_data: Dict[str, Any]) -> PlannedMeal:
        """Convert dict → PlannedMeal; tolerate missing keys."""
        try:
            meal_type = MealType(meal_data["meal_type"].lower())
        except (KeyError, ValueError):
            logger.warning("Unknown or missing meal_type – defaulting to BREAKFAST")
            meal_type = MealType.BREAKFAST

        return PlannedMeal(
            meal_type=meal_type,
            name=meal_data.get("name", "Unnamed meal"),
            description=meal_data.get("description", ""),
            prep_time=meal_data.get("prep_time", 0),
            cook_time=meal_data.get("cook_time", 0),
            calories=meal_data.get("calories", 0),
            protein=meal_data.get("protein", 0.0),
            carbs=meal_data.get("carbs", 0.0),
            fat=meal_data.get("fat", 0.0),
            ingredients=meal_data.get("ingredients", []),
            instructions=meal_data.get("instructions", []),
            is_vegetarian=meal_data.get("is_vegetarian", False),
            is_vegan=meal_data.get("is_vegan", False),
            is_gluten_free=meal_data.get("is_gluten_free", False),
            cuisine_type=meal_data.get("cuisine_type", "International"),
        )


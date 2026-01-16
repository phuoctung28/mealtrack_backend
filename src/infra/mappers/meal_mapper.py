"""
Mappers for converting between Meal domain models and SQLAlchemy persistence models.
"""
from src.domain.model.meal.meal import Meal as DomainMeal, MealStatus
from src.domain.model.meal.meal_image import MealImage as DomainMealImage
from src.domain.model.nutrition import Nutrition as DomainNutrition, Macros, Micros, FoodItem
from src.infra.database.models.meal.meal import Meal as DBMeal
from src.infra.database.models.meal.meal_image import MealImage as DBMealImage
from src.infra.database.models.nutrition.nutrition import Nutrition as DBNutrition
from src.infra.database.models.nutrition.food_item import FoodItem as DBFoodItem
from src.infra.mappers import MealStatusMapper
from src.domain.utils.timezone_utils import utc_now


class MealMapper:
    """Mapper for Meal entity."""

    @staticmethod
    def to_domain(db_meal: DBMeal) -> DomainMeal:
        """Convert DB model to domain model."""
        return DomainMeal(
            meal_id=db_meal.meal_id,
            user_id=db_meal.user_id,
            status=MealStatusMapper.to_domain(db_meal.status),
            created_at=db_meal.created_at,
            image=MealImageMapper.to_domain(db_meal.image) if db_meal.image else None,
            dish_name=db_meal.dish_name,
            nutrition=NutritionMapper.to_domain(db_meal.nutrition) if db_meal.nutrition else None,
            ready_at=db_meal.ready_at,
            error_message=db_meal.error_message,
            raw_gpt_json=db_meal.raw_ai_response,
            updated_at=db_meal.updated_at,
            last_edited_at=db_meal.last_edited_at,
            edit_count=db_meal.edit_count,
            is_manually_edited=db_meal.is_manually_edited,
            meal_type=None # meal_type might be missing in DB model, strictly speaking
        )

    @staticmethod
    def to_persistence(domain_meal: DomainMeal) -> DBMeal:
        """Convert domain model to DB model."""
        # Note: Relationships (image, nutrition) are typically handled separately 
        # or require careful management in SQLAlchemy
        
        return DBMeal(
            meal_id=str(domain_meal.meal_id),
            user_id=str(domain_meal.user_id),
            status=MealStatusMapper.to_db(domain_meal.status),
            created_at=domain_meal.created_at,
            updated_at=domain_meal.updated_at or utc_now(),
            dish_name=domain_meal.dish_name,
            ready_at=domain_meal.ready_at,
            error_message=domain_meal.error_message,
            raw_ai_response=domain_meal.raw_gpt_json,
            last_edited_at=domain_meal.last_edited_at,
            edit_count=domain_meal.edit_count,
            is_manually_edited=domain_meal.is_manually_edited,
            # image_id and nutrition_id are handled by repository logic or ORM
        )


class MealImageMapper:
    """Mapper for MealImage entity."""

    @staticmethod
    def to_domain(db_image: DBMealImage) -> DomainMealImage:
        return DomainMealImage(
            image_id=db_image.image_id,
            url=db_image.url,
            format=db_image.format,
            size_bytes=db_image.size_bytes,
            width=db_image.width,
            height=db_image.height
        )

    @staticmethod
    def to_persistence(domain_image: DomainMealImage) -> DBMealImage:
        return DBMealImage(
            image_id=str(domain_image.image_id),
            url=domain_image.url,
            format=domain_image.format,
            size_bytes=domain_image.size_bytes,
            width=domain_image.width,
            height=domain_image.height
        )


class NutritionMapper:
    """Mapper for Nutrition entity."""

    @staticmethod
    def to_domain(db_nutrition: DBNutrition) -> DomainNutrition:
        food_items = []
        if db_nutrition.food_items:
            food_items = [FoodItemMapper.to_domain(item) for item in db_nutrition.food_items]

        # Construct Macros from DB columns
        macros = Macros(
            protein=db_nutrition.protein,
            carbs=db_nutrition.carbs,
            fat=db_nutrition.fat
        )
        
        # Construct Micros (assuming simple mapping or None for now)
        micros = None # Populate if DB has micro columns or relationship

        return DomainNutrition(
            calories=db_nutrition.calories,
            macros=macros,
            micros=micros,
            food_items=food_items,
            confidence_score=db_nutrition.confidence_score
        )

    @staticmethod
    def to_persistence(domain_nutrition: DomainNutrition, meal_id: str) -> DBNutrition:
        return DBNutrition(
            meal_id=meal_id,
            calories=domain_nutrition.calories,
            protein=domain_nutrition.macros.protein,
            carbs=domain_nutrition.macros.carbs,
            fat=domain_nutrition.macros.fat,
            confidence_score=domain_nutrition.confidence_score,
            # food_items handled by repository
        )


class FoodItemMapper:
    """Mapper for FoodItem entity."""

    @staticmethod
    def to_domain(db_item: DBFoodItem) -> FoodItem:
        macros = Macros(
            protein=db_item.protein,
            carbs=db_item.carbs,
            fat=db_item.fat
        )
        return FoodItem(
            id=str(db_item.id),  # Required parameter
            name=db_item.name,
            quantity=db_item.quantity,
            unit=db_item.unit,
            calories=db_item.calories,
            macros=macros,
            micros=None, # Populate if needed
            confidence=db_item.confidence,
            fdc_id=db_item.fdc_id,
            is_custom=bool(db_item.is_custom),
            # Additional fields if present in Domain but not DB or vice versa
        )

    @staticmethod
    def to_persistence(domain_item: FoodItem, nutrition_id: str) -> DBFoodItem:
        return DBFoodItem(
            nutrition_id=nutrition_id,
            name=domain_item.name,
            quantity=domain_item.quantity,
            unit=domain_item.unit,
            calories=domain_item.calories,
            protein=domain_item.macros.protein,
            carbs=domain_item.macros.carbs,
            fat=domain_item.macros.fat,
            confidence=domain_item.confidence,
            # Handle FDC ID and custom flags if available
            fdc_id=getattr(domain_item, 'fdc_id', None),
            is_custom=getattr(domain_item, 'is_custom', False)
        )

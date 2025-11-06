"""
Command handlers for meal domain - write operations.
"""
import logging
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from src.api.exceptions import ValidationException, ResourceNotFoundException
from src.app.commands.meal import (
    UploadMealImageCommand,
    RecalculateMealNutritionCommand,
    EditMealCommand,
    AddCustomIngredientCommand
)
from src.app.commands.meal.delete_meal_command import DeleteMealCommand
from src.app.events.base import EventHandler, handles
from src.app.events.meal import (
    MealImageUploadedEvent,
    MealNutritionUpdatedEvent,
    MealEditedEvent
)
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal import MealImage
from src.domain.model.nutrition import FoodItem, Macros
from src.domain.ports.image_store_port import ImageStorePort
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.infra.services.pinecone_service import get_pinecone_service

logger = logging.getLogger(__name__)


@handles(UploadMealImageCommand)
class UploadMealImageCommandHandler(EventHandler[UploadMealImageCommand, Dict[str, Any]]):
    """Handler for uploading meal images."""
    
    def __init__(self, meal_repository: MealRepositoryPort = None, image_store: ImageStorePort = None):
        self.meal_repository = meal_repository
        self.image_store = image_store
    
    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
        self.image_store = kwargs.get('image_store', self.image_store)
    
    async def handle(self, command: UploadMealImageCommand) -> Dict[str, Any]:
        """Upload meal image and create meal record."""
        if not self.meal_repository or not self.image_store:
            raise RuntimeError("Dependencies not configured")
        
        # Upload image
        image_id = self.image_store.save(
            command.file_contents,
            command.content_type
        )
        
        # Get image URL
        image_url = self.image_store.get_url(image_id)
        
        # Create meal image
        meal_image = MealImage(
            image_id=image_id,
            format="jpeg" if command.content_type == "image/jpeg" else "png",
            size_bytes=len(command.file_contents),
            url=image_url or f"mock://images/{image_id}"
        )
        
        # Create meal
        meal = Meal(
            meal_id=str(uuid4()),
            user_id=command.user_id,
            status=MealStatus.PROCESSING,
            created_at=datetime.now(),
            image=meal_image
        )
        
        # Save meal
        saved_meal = self.meal_repository.save(meal)
        
        return {
            "meal_id": saved_meal.meal_id,
            "status": saved_meal.status.value,
            "image_url": saved_meal.image.url if saved_meal.image else None,
            "events": [
                MealImageUploadedEvent(
                    aggregate_id=saved_meal.meal_id,
                    meal_id=saved_meal.meal_id,
                    image_url=meal_image.url,
                    upload_timestamp=datetime.now()
                )
            ]
        }


@handles(RecalculateMealNutritionCommand)
class RecalculateMealNutritionCommandHandler(EventHandler[RecalculateMealNutritionCommand, Dict[str, Any]]):
    """Handler for recalculating meal nutrition based on weight."""

    def __init__(self, meal_repository: MealRepositoryPort = None, pinecone_service=None):
        self.meal_repository = meal_repository
        self.pinecone_service = pinecone_service

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
        self.pinecone_service = kwargs.get('pinecone_service', self.pinecone_service)
    
    async def handle(self, command: RecalculateMealNutritionCommand) -> Dict[str, Any]:
        """Recalculate meal nutrition using Pinecone for fresh ingredient data."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")
        
        # Validate weight
        if command.weight_grams <= 0:
            raise ValidationException("Weight must be greater than 0")
        
        # Get meal
        meal = self.meal_repository.find_by_id(command.meal_id)
        if not meal:
            raise ResourceNotFoundException(f"Meal with ID {command.meal_id} not found")
        
        if not meal.nutrition or not meal.nutrition.food_items:
            raise ValidationException(f"Meal {command.meal_id} has no food items to recalculate")
        
        # Use Pinecone to recalculate nutrition for all ingredients
        try:
            # Use injected service, fallback to get_pinecone_service if not injected
            pinecone_svc = self.pinecone_service or get_pinecone_service()

            # Calculate total nutrition using Pinecone
            total_nutrition = pinecone_svc.calculate_total_nutrition([
                {
                    'name': item.name,
                    'quantity': item.quantity,
                    'unit': item.unit
                }
                for item in meal.nutrition.food_items
            ])
            
            # Update meal nutrition with Pinecone-calculated values
            meal.nutrition.calories = total_nutrition.calories
            meal.nutrition.macros.protein = total_nutrition.protein
            meal.nutrition.macros.carbs = total_nutrition.carbs
            meal.nutrition.macros.fat = total_nutrition.fat
            
        except Exception as e:
            logger.error(f"Error using Pinecone for recalculation: {e}")
            # Fall back to simple scaling if Pinecone fails
            old_weight = getattr(meal, 'weight_grams', 100.0)
            scale_factor = command.weight_grams / old_weight
            
            meal.nutrition.calories = meal.nutrition.calories * scale_factor
            meal.nutrition.macros.protein = meal.nutrition.macros.protein * scale_factor
            meal.nutrition.macros.carbs = meal.nutrition.macros.carbs * scale_factor
            meal.nutrition.macros.fat = meal.nutrition.macros.fat * scale_factor
        
        # Save updated meal
        updated_meal = self.meal_repository.save(meal)
        
        # Prepare nutrition data for response
        nutrition_data = {
            "calories": round(updated_meal.nutrition.calories, 1),
            "protein": round(updated_meal.nutrition.macros.protein, 1),
            "carbs": round(updated_meal.nutrition.macros.carbs, 1),
            "fat": round(updated_meal.nutrition.macros.fat, 1)
        }
        
        return {
            "meal_id": command.meal_id,
            "updated_nutrition": nutrition_data,
            "weight_grams": command.weight_grams,
            "events": [
                MealNutritionUpdatedEvent(
                    aggregate_id=command.meal_id,
                    meal_id=command.meal_id,
                    old_weight=getattr(meal, 'weight_grams', 100.0),
                    new_weight=command.weight_grams,
                    updated_nutrition=nutrition_data
                )
            ]
        }


@handles(EditMealCommand)
class EditMealCommandHandler(EventHandler[EditMealCommand, Dict[str, Any]]):
    """Handler for editing meal ingredients."""

    def __init__(self,
                 meal_repository: MealRepositoryPort = None,
                 food_service=None,
                 nutrition_calculator=None,
                 pinecone_service=None):
        self.meal_repository = meal_repository
        self.food_service = food_service
        self.nutrition_calculator = nutrition_calculator
        self.pinecone_service = pinecone_service

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
        self.food_service = kwargs.get('food_service', self.food_service)
        self.nutrition_calculator = kwargs.get('nutrition_calculator', self.nutrition_calculator)
        self.pinecone_service = kwargs.get('pinecone_service', self.pinecone_service)
    
    async def handle(self, command: EditMealCommand) -> Dict[str, Any]:
        """Handle meal editing operations."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")
        
        # 1. Validate meal exists
        meal = self.meal_repository.find_by_id(command.meal_id)
        if not meal:
            from src.api.exceptions import ResourceNotFoundException
            raise ResourceNotFoundException("Meal not found")
        
        if meal.status != MealStatus.READY:
            raise ValidationException("Meal must be in READY status to edit")
        
        # 2. Apply food item changes
        updated_food_items = await self._apply_food_item_changes(
            meal.nutrition.food_items if meal.nutrition else [],
            command.food_item_changes
        )
        
        # 3. Recalculate nutrition
        updated_nutrition = self._calculate_total_nutrition(updated_food_items)
        
        # 4. Update meal
        updated_meal = meal.mark_edited(
            nutrition=updated_nutrition,
            dish_name=command.dish_name or meal.dish_name
        )
        
        # 5. Persist changes
        saved_meal = self.meal_repository.save(updated_meal)
        
        # 6. Calculate nutrition delta for event
        nutrition_delta = self._calculate_nutrition_delta(meal.nutrition, updated_nutrition)
        
        # 7. Generate changes summary
        changes_summary = self._generate_changes_summary(command.food_item_changes)
        
        return {
            "success": True,
            "meal_id": saved_meal.meal_id,
            "message": f"Meal updated successfully. {changes_summary}",
            "dish_name": saved_meal.dish_name or "Meal",
            "total_calories": updated_nutrition.calories,
            "updated_nutrition": {
                "calories": updated_nutrition.calories,
                "protein": updated_nutrition.macros.protein,
                "carbs": updated_nutrition.macros.carbs,
                "fat": updated_nutrition.macros.fat,
            },
            "updated_food_items": [item.to_dict() for item in updated_food_items],
            "edit_metadata": {
                "edit_count": saved_meal.edit_count,
                "changes_summary": changes_summary
            },
            "events": [
                MealEditedEvent(
                    aggregate_id=saved_meal.meal_id,
                    meal_id=saved_meal.meal_id,
                    user_id=saved_meal.user_id,
                    edit_type="ingredients_updated",
                    changes_summary=changes_summary,
                    nutrition_delta=nutrition_delta,
                    edit_count=saved_meal.edit_count
                )
            ]
        }
    
    async def _apply_food_item_changes(self, current_food_items, changes):
        """Apply food item changes to current list using strategy pattern."""
        from src.domain.services import NutritionCalculationService
        from src.app.handlers.command_handlers.meal_edit_strategies import FoodItemChangeStrategyFactory

        # Convert current items to dict for easier manipulation
        food_items_dict = {}
        if current_food_items:
            for item in current_food_items:
                food_items_dict[item.id] = item

        # Initialize nutrition service and create strategies
        nutrition_service = NutritionCalculationService(
            pinecone_service=self.pinecone_service or get_pinecone_service(),
            usda_service=self.food_service
        )
        strategies = FoodItemChangeStrategyFactory.create_strategies(
            nutrition_service,
            self.food_service
        )

        # Apply each change using the appropriate strategy
        for change in changes:
            if change.action == "remove" and change.id:
                food_items_dict.pop(change.id, None)
            
            elif change.action == "update" and change.id:
                if change.id in food_items_dict:
                    existing_item = food_items_dict[change.id]
                    new_quantity = change.quantity or existing_item.quantity
                    
                    # If custom nutrition is provided, recalculate from per-100g values
                    if change.custom_nutrition:
                        scale_factor = new_quantity / 100.0
                        nutrition = change.custom_nutrition
                        
                        food_items_dict[change.id] = FoodItem(
                            id=existing_item.id,
                            name=change.name or existing_item.name,
                            quantity=new_quantity,
                            unit=change.unit or existing_item.unit,
                            calories=nutrition.calories_per_100g * scale_factor,
                            macros=Macros(
                                protein=nutrition.protein_per_100g * scale_factor,
                                carbs=nutrition.carbs_per_100g * scale_factor,
                                fat=nutrition.fat_per_100g * scale_factor,
                            ),
                            micros=existing_item.micros,
                            confidence=existing_item.confidence if existing_item.is_custom else 0.8,
                            fdc_id=existing_item.fdc_id,
                            is_custom=True
                        )
                    else:
                        # Update quantity and recalculate nutrition by scaling
                        scale_factor = new_quantity / existing_item.quantity
                        
                        food_items_dict[change.id] = FoodItem(
                            id=existing_item.id,  # Preserve the existing ID
                            name=change.name or existing_item.name,
                            quantity=new_quantity,
                            unit=change.unit or existing_item.unit,
                            calories=existing_item.calories * scale_factor,
                            macros=Macros(
                                protein=existing_item.macros.protein * scale_factor,
                                carbs=existing_item.macros.carbs * scale_factor,
                                fat=existing_item.macros.fat * scale_factor,
                            ),
                            micros=existing_item.micros,
                            confidence=existing_item.confidence,
                            fdc_id=existing_item.fdc_id,
                            is_custom=existing_item.is_custom
                        )
            
            elif change.action == "add":
                new_item_id = str(uuid4())
                
                if change.fdc_id and self.food_service:
                    # Get nutrition from USDA
                    usda_food = await self._get_usda_food_nutrition(change.fdc_id, change.quantity or 100)
                    food_items_dict[new_item_id] = usda_food
                elif change.custom_nutrition:
                    # Create custom food item
                    scale_factor = (change.quantity or 100) / 100.0
                    nutrition = change.custom_nutrition
                    
                    food_items_dict[new_item_id] = FoodItem(
                        id=new_item_id,  # Use generated ID
                        name=change.name or "Custom Ingredient",
                        quantity=change.quantity or 100,
                        unit=change.unit or "g",
                        calories=nutrition.calories_per_100g * scale_factor,
                        macros=Macros(
                            protein=nutrition.protein_per_100g * scale_factor,
                            carbs=nutrition.carbs_per_100g * scale_factor,
                            fat=nutrition.fat_per_100g * scale_factor,
                        ),
                        confidence=0.8,  # Custom ingredients have lower confidence
                        fdc_id=None,
                        is_custom=True
                    )
        
        return list(food_items_dict.values())
    
    async def _get_usda_food_nutrition(self, fdc_id: int, quantity: float):
        """Get nutrition data from USDA service."""
        import uuid
        
        if not self.food_service:
            raise RuntimeError("Food service not configured")
        
        # Get food details from USDA
        food_data = await self.food_service.get_food_details(fdc_id)
        
        # Extract nutrition data (per 100g basis)
        nutrients = food_data.get('foodNutrients', [])
        
        # Map USDA nutrient IDs to our fields
        nutrient_map = {
            1008: 'calories',  # Energy (cal)
            1003: 'protein',   # Protein
            1005: 'carbs',     # Carbohydrate, by difference
            1004: 'fat'        # Total lipid (fat)
        }
        
        nutrition_values = {}
        for nutrient in nutrients:
            nutrient_id = nutrient.get('nutrient', {}).get('id')
            if nutrient_id in nutrient_map:
                nutrition_values[nutrient_map[nutrient_id]] = nutrient.get('amount', 0)
        
        # Calculate nutrition for the specified quantity
        scale_factor = quantity / 100.0  # USDA data is per 100g
        
        return FoodItem(
            id=str(uuid.uuid4()),  # Generate new ID for USDA food
            name=food_data.get('description', f"USDA Food {fdc_id}"),
            quantity=quantity,
            unit="g",
            calories=nutrition_values.get('calories', 0) * scale_factor,
            macros=Macros(
                protein=nutrition_values.get('protein', 0) * scale_factor,
                carbs=nutrition_values.get('carbs', 0) * scale_factor,
                fat=nutrition_values.get('fat', 0) * scale_factor,
            ),
            confidence=1.0,
            fdc_id=fdc_id,
            is_custom=False
        )
    
    def _calculate_total_nutrition(self, food_items):
        """Calculate total nutrition from food items using nutrition service."""
        from src.domain.services import NutritionCalculationService

        nutrition_service = NutritionCalculationService()
        return nutrition_service.calculate_meal_total(food_items)
    
    def _calculate_nutrition_delta(self, old_nutrition, new_nutrition):
        """Calculate the difference in nutrition values."""
        if not old_nutrition:
            return {
                "calories": new_nutrition.calories,
                "protein": new_nutrition.macros.protein,
                "carbs": new_nutrition.macros.carbs,
                "fat": new_nutrition.macros.fat
            }
        
        return {
            "calories": new_nutrition.calories - old_nutrition.calories,
            "protein": new_nutrition.macros.protein - old_nutrition.macros.protein,
            "carbs": new_nutrition.macros.carbs - old_nutrition.macros.carbs,
            "fat": new_nutrition.macros.fat - old_nutrition.macros.fat
        }
    
    def _generate_changes_summary(self, changes):
        """Generate a human-readable summary of changes."""
        summary_parts = []
        for change in changes:
            if change.action == "add":
                summary_parts.append(f"Added {change.name or 'ingredient'}")
            elif change.action == "remove":
                summary_parts.append("Removed ingredient")
            elif change.action == "update":
                summary_parts.append("Updated portion")
        
        return "; ".join(summary_parts) if summary_parts else "Updated meal"


@handles(AddCustomIngredientCommand)
class AddCustomIngredientCommandHandler(EventHandler[AddCustomIngredientCommand, Dict[str, Any]]):
    """Handler for adding custom ingredients to meals."""
    
    def __init__(self, meal_repository: MealRepositoryPort = None):
        self.meal_repository = meal_repository
    
    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
    
    async def handle(self, command: AddCustomIngredientCommand) -> Dict[str, Any]:
        """Handle adding custom ingredient to meal."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")
        
        # Delegate to EditMealCommand with custom ingredient
        from src.app.commands.meal import FoodItemChange
        
        edit_command = EditMealCommand(
            meal_id=command.meal_id,
            food_item_changes=[
                FoodItemChange(
                    action="add",
                    name=command.name,
                    quantity=command.quantity,
                    unit=command.unit,
                    custom_nutrition=command.nutrition
                )
            ]
        )
        
        # Use the edit handler
        edit_handler = EditMealCommandHandler(self.meal_repository)
        return await edit_handler.handle(edit_command)


@handles(DeleteMealCommand)
class DeleteMealCommandHandler(EventHandler[DeleteMealCommand, Dict[str, Any]]):
    """Handler for soft-deleting a meal (marking as INACTIVE)."""
    def __init__(self, meal_repository: MealRepositoryPort = None):
        self.meal_repository = meal_repository

    def set_dependencies(self, **kwargs):
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)

    async def handle(self, command: DeleteMealCommand) -> Dict[str, Any]:
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")
        meal = self.meal_repository.find_by_id(command.meal_id)
        if not meal:
            raise ResourceNotFoundException(f"Meal with ID {command.meal_id} not found")
        inactive_meal = meal.mark_inactive()
        self.meal_repository.save(inactive_meal)
        return {
            "meal_id": inactive_meal.meal_id,
            "status": inactive_meal.status.value,
            "message": "Meal marked as inactive"
        }
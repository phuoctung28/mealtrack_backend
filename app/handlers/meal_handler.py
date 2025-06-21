import uuid
from datetime import datetime
from typing import Optional, Dict, Any, BinaryIO

from domain.model.meal import Meal, MealStatus
from domain.model.meal_image import MealImage
from domain.ports.image_store_port import ImageStorePort
from domain.ports.meal_repository_port import MealRepositoryPort


class MealHandler:
    """
    Application handler for meal-related operations.
    
    This class coordinates between the API layer and the domain layer,
    implementing use cases for meal management.
    """
    
    def __init__(
        self,
        meal_repository: MealRepositoryPort,
        image_store: ImageStorePort
    ):
        """
        Initialize the handler with dependencies.
        
        Args:
            meal_repository: Repository for meal data
            image_store: Service for storing images
        """
        self.meal_repository = meal_repository
        self.image_store = image_store
    
    def upload_meal_image(
        self,
        image_file: BinaryIO,
        image_format: str,
        image_size: int,
        width: int,
        height: int
    ) -> Meal:
        """
        Upload a meal image and create a new meal.
        
        This method implements US-1.1 through US-1.4.
        
        Args:
            image_file: The image file content
            image_format: The image format (e.g., 'jpeg', 'png')
            image_size: Size of the image in bytes
            width: Width of the image in pixels
            height: Height of the image in pixels
            
        Returns:
            The created meal entity
        """
        # Generate unique IDs
        image_id = str(uuid.uuid4())
        meal_id = str(uuid.uuid4())
        
        # Store the image
        image_bytes = image_file.read()
        self.image_store.save(image_id, image_bytes)
        
        # Create the meal image
        meal_image = MealImage(
            image_id=image_id,
            format=image_format,
            size_bytes=image_size,
            width=width,
            height=height
        )
        
        # Create the meal
        meal = Meal(
            meal_id=meal_id,
            status=MealStatus.PROCESSING,
            created_at=datetime.now(),
            image=meal_image
        )
        
        # Save the meal
        self.meal_repository.save(meal)
        
        return meal
    
    def get_meal(self, meal_id: str) -> Optional[Meal]:
        """
        Get a meal by ID.
        
        This method implements US-2.3.
        
        Args:
            meal_id: ID of the meal to retrieve
            
        Returns:
            The meal if found, None otherwise
        """
        return self.meal_repository.find_by_id(meal_id)
    
    def update_meal_weight(self, meal_id: str, weight_grams: float) -> Optional[Meal]:
        """
        Update meal with new weight and recalculate nutrition.
        
        Args:
            meal_id: ID of the meal to update
            weight_grams: New weight in grams
            
        Returns:
            The updated meal if found, None otherwise
        """
        # Get the existing meal
        meal = self.meal_repository.find_by_id(meal_id)
        if not meal:
            return None
        
        # Calculate scaling factor from original weight
        original_weight = 300.0  # Default weight in grams
        if meal.nutrition and hasattr(meal.nutrition, 'food_items') and meal.nutrition.food_items:
            first_food = meal.nutrition.food_items[0]
            if first_food.unit and 'g' in first_food.unit.lower():
                original_weight = first_food.quantity
            elif first_food.quantity > 10:
                original_weight = first_food.quantity
        
        # Create updated meal with new weight
        # Mark it for LLM recalculation rather than just scaling
        updated_meal = Meal(
            meal_id=meal.meal_id,
            status=MealStatus.ANALYZING,  # Mark for LLM recalculation
            created_at=meal.created_at,
            updated_at=datetime.now(),
            image=meal.image,
            nutrition=meal.nutrition,  # Keep existing nutrition temporarily
            error_message=None
        )
        
        # Store the new weight information for LLM context
        # This will be used by the background LLM analysis
        setattr(updated_meal, 'updated_weight_grams', weight_grams)
        setattr(updated_meal, 'original_weight_grams', original_weight)
        
        # Save the updated meal
        self.meal_repository.save(updated_meal)
        
        return updated_meal
    
    def update_meal_with_llm_nutrition(self, meal_id: str, nutrition_data: Dict[str, Any]) -> Optional[Meal]:
        """
        Update meal with new nutrition data from LLM analysis.
        
        Args:
            meal_id: ID of the meal to update
            nutrition_data: Nutrition data from LLM analysis
            
        Returns:
            The updated meal if found, None otherwise
        """
        from domain.model.nutrition import Nutrition
        from domain.model.food_item import FoodItem
        from domain.model.macros import Macros
        
        # Get the existing meal
        meal = self.meal_repository.find_by_id(meal_id)
        if not meal:
            return None
        
        try:
            # Parse nutrition data from LLM response
            structured_data = nutrition_data.get("structured_data", {})
            
            # Store the dish_name if available
            dish_name = structured_data.get("dish_name", None)
            
            # Create food items
            food_items = []
            for food_data in structured_data.get("foods", []):
                macros = Macros(
                    protein=food_data.get("macros", {}).get("protein", 0.0),
                    carbs=food_data.get("macros", {}).get("carbs", 0.0),
                    fat=food_data.get("macros", {}).get("fat", 0.0),
                    fiber=food_data.get("macros", {}).get("fiber", 0.0)
                )
                
                food_item = FoodItem(
                    name=food_data.get("name", "Unknown Food"),
                    quantity=food_data.get("quantity", 0.0),
                    unit=food_data.get("unit", "g"),
                    calories=food_data.get("calories", 0.0),
                    macros=macros,
                    confidence=structured_data.get("confidence", 0.8)
                )
                food_items.append(food_item)
            
            # Calculate total macros
            total_macros = Macros(
                protein=sum(item.macros.protein for item in food_items),
                carbs=sum(item.macros.carbs for item in food_items),
                fat=sum(item.macros.fat for item in food_items),
                fiber=sum(item.macros.fiber for item in food_items if item.macros.fiber)
            )
            
            # Create nutrition object
            nutrition = Nutrition(
                calories=structured_data.get("total_calories", sum(item.calories for item in food_items)),
                macros=total_macros,
                food_items=food_items,
                confidence_score=structured_data.get("confidence", 0.8)
            )
            
            # Create updated meal with new nutrition
            updated_meal = Meal(
                meal_id=meal.meal_id,
                status=MealStatus.READY,  # Mark as ready with new nutrition
                created_at=meal.created_at,
                updated_at=datetime.now(),
                image=meal.image,
                nutrition=nutrition,
                error_message=None
            )
            
            # Preserve weight metadata if it exists
            if hasattr(meal, 'updated_weight_grams'):
                setattr(updated_meal, 'updated_weight_grams', meal.updated_weight_grams)
            if hasattr(meal, 'original_weight_grams'):
                setattr(updated_meal, 'original_weight_grams', meal.original_weight_grams)
            
            # Save the updated meal
            self.meal_repository.save(updated_meal)
            
            return updated_meal
            
        except Exception as e:
            # Mark meal as failed if nutrition update fails
            failed_meal = Meal(
                meal_id=meal.meal_id,
                status=MealStatus.FAILED,
                created_at=meal.created_at,
                updated_at=datetime.now(),
                image=meal.image,
                nutrition=meal.nutrition,  # Keep existing nutrition
                error_message=f"Failed to update nutrition: {str(e)}"
            )
            
            self.meal_repository.save(failed_meal)
            return None 
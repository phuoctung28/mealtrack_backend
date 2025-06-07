import uuid
from datetime import datetime
from typing import Optional, BinaryIO

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
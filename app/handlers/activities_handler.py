import logging
from typing import List, Dict, Any

from domain.model.meal import Meal
from domain.ports.meal_repository_port import MealRepositoryPort

logger = logging.getLogger(__name__)

class ActivitiesHandler:
    """
    Application handler for activity-related operations.
    
    This class coordinates between the API layer and the domain layer,
    implementing use cases for activity tracking and retrieval.
    Follows the mediator pattern to decouple API concerns from business logic.
    """
    
    def __init__(self, meal_repository: MealRepositoryPort):
        """
        Initialize the handler with dependencies.
        
        Args:
            meal_repository: Repository for meal data
        """
        self.meal_repository = meal_repository
    
    def get_user_activities(
        self, 
        page: int = 1, 
        page_size: int = 20, 
    ) -> Dict[str, Any]:
        """
        Retrieve user activities with pagination and optional status filtering.
        
        This method implements the core business logic for activity retrieval,
        transforming meal data into enriched activity format.
        
        Args:
            page: Page number (starts from 1)
            page_size: Number of items per page (1-100)

        Returns:
            Dictionary containing activities, pagination metadata, and endpoint metadata
            
        Raises:
            ValueError: If pagination parameters are invalid
            KeyError: If status parameter is invalid
        """
        # Validate pagination parameters
        if page < 1:
            raise ValueError("Page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise ValueError("Page size must be between 1 and 100")
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get meals based on status filter
        meals, total_count = self._get_filtered_meals(offset, page_size)
        
        # Calculate pagination metadata
        pagination = self._calculate_pagination_metadata(page, page_size, total_count)
        
        # Create endpoint metadata
        metadata = self._create_endpoint_metadata()
        
        # Return raw data for API layer to convert to DTO
        return {
            "meals": meals,
            "pagination": pagination,
            "metadata": metadata
        }
    
    def _get_filtered_meals(
        self, 
        offset: int,
        page_size: int
    ) -> tuple[List[Meal], int]:
        """
        Get meals based on status filter with pagination.
        
        Args:
            status: Optional status filter
            offset: Pagination offset
            page_size: Page size
            
        Returns:
            Tuple of (meals list, total count)
        """
        meals = self.meal_repository.find_all_paginated(offset=offset, limit=page_size)
        total_count = self.meal_repository.count()
        
        return meals, total_count
    

    

    
    def _calculate_pagination_metadata(
        self, 
        page: int, 
        page_size: int, 
        total_count: int
    ) -> Dict[str, Any]:
        """
        Calculate pagination metadata.
        
        Args:
            page: Current page number
            page_size: Items per page
            total_count: Total number of items
            
        Returns:
            Dictionary containing pagination metadata
        """
        total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
        has_next = page < total_pages
        has_previous = page > 1
        
        return {
            "current_page": page,
            "page_size": page_size,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_previous": has_previous,
            "next_page": page + 1 if has_next else None,
            "previous_page": page - 1 if has_previous else None
        }
    
    def _create_endpoint_metadata(self) -> Dict[str, Any]:
        """
        Create metadata about the endpoint capabilities.
        
        Returns:
            Dictionary containing endpoint metadata
        """
        return {
            "endpoint_version": "v1",
            "scalable_design": True,
            "supported_activity_types": ["MEAL_SCAN", "MEAL_SCAN_FAILED"],
            "future_activity_types": ["MANUAL_FOOD_ADD", "TRAINING_SESSION", "BODY_SCAN"],
            "enrichment_level": "full_nutrition_data"
        } 
"""
Activity Mapper

Handles conversion between Activity domain models and DTOs.
Follows the Mapper Pattern for clean separation of concerns.
"""

from typing import Dict, Any, List

from api.schemas import (
    ActivityResponse,
    ActivityEnrichedData,
    ActivitiesResponse,
    ImageSchema
)
from app.models import PaginationMetadata, MacrosSchema
from domain.model.meal import Meal, MealStatus


class ActivityMapper:
    """
    Mapper class for converting between Activity/Meal domain models and activity DTOs.
    
    This class encapsulates all the conversion logic for activity tracking,
    keeping handlers focused on business orchestration.
    """
    
    @staticmethod
    def to_activities_response(
        activities: List[Dict[str, Any]], 
        pagination: Dict[str, Any], 
        metadata: Dict[str, Any]
    ) -> ActivitiesResponse:
        """
        Convert activities data to ActivitiesResponse DTO.
        
        Args:
            activities: List of activity dictionaries
            pagination: Pagination metadata dictionary
            metadata: Endpoint metadata dictionary
            
        Returns:
            ActivitiesResponse DTO
        """
        # Convert activities
        activity_responses = [
            ActivityMapper._to_activity_response(activity) for activity in activities
        ]
        
        # Convert pagination metadata
        pagination_metadata = PaginationMetadata(
            current_page=pagination["current_page"],
            page_size=pagination["page_size"],
            total_items=pagination["total_items"],
            total_pages=pagination["total_pages"],
            has_next=pagination["has_next"],
            has_previous=pagination["has_previous"],
            next_page=pagination.get("next_page"),
            previous_page=pagination.get("previous_page")
        )

        
        return ActivitiesResponse(
            activities=activity_responses,
            pagination=pagination_metadata,
        )
    
    @staticmethod
    def meal_to_activity(meal: Meal) -> Dict[str, Any]:
        """
        Convert a Meal domain model to an activity dictionary.
        
        Args:
            meal: Domain meal model
            
        Returns:
            Activity dictionary
        """
        # Create base activity data
        activity = {
            "activity_id": meal.meal_id,  # Using meal_id as activity_id for now
            "activity_type": "MEAL_SCAN" if meal.status != MealStatus.FAILED else "MEAL_SCAN_FAILED",
            "meal_id": meal.meal_id,
            "status": meal.status.value,
            "created_at": meal.created_at.isoformat() if meal.created_at else None,
            "ready_at": meal.ready_at.isoformat() if meal.ready_at else None,
        }
        
        # Add enriched meal data if available
        if meal.nutrition:
            enriched_data = ActivityMapper._create_enriched_nutrition_data(meal)
            activity.update({
                "title": f"Scanned meal: {enriched_data['meal_name']}",
                "description": f"AI-identified meal with {enriched_data['total_calories']:.0f} calories",
                "enriched_data": enriched_data
            })
        else:
            # Basic activity data for meals without nutrition
            title, description = ActivityMapper._create_basic_activity_data(meal)
            activity.update({
                "title": title,
                "description": description,
                "enriched_data": None
            })
        
        # Add image information
        if meal.image:
            activity["image"] = ActivityMapper._create_image_data(meal.image)
        
        # Add error information if applicable
        if meal.error_message:
            activity["error_message"] = meal.error_message
        
        return activity
    
    @staticmethod
    def _to_activity_response(activity_dict: Dict[str, Any]) -> ActivityResponse:
        """
        Convert an activity dictionary to ActivityResponse DTO.
        
        Args:
            activity_dict: Activity dictionary
            
        Returns:
            ActivityResponse DTO
        """
        # Convert enriched data if present
        enriched_data = None
        if activity_dict.get("enriched_data"):
            enriched_data = ActivityEnrichedData(
                meal_name=activity_dict["enriched_data"]["meal_name"],
                total_calories=activity_dict["enriched_data"]["total_calories"],
                weight_grams=activity_dict["enriched_data"]["weight_grams"],
                calories_per_100g=activity_dict["enriched_data"]["calories_per_100g"],
                macros=MacrosSchema(**activity_dict["enriched_data"]["macros"]),
                confidence_score=activity_dict["enriched_data"]["confidence_score"],
                food_items_count=activity_dict["enriched_data"]["food_items_count"]
            )
        
        # Convert image if present
        image = None
        if activity_dict.get("image"):
            image = ImageSchema(**activity_dict["image"])
        
        return ActivityResponse(
            activity_id=activity_dict["activity_id"],
            activity_type=activity_dict["activity_type"],
            meal_id=activity_dict["meal_id"],
            status=activity_dict["status"],
            title=activity_dict["title"],
            description=activity_dict["description"],
            created_at=activity_dict.get("created_at"),
            ready_at=activity_dict.get("ready_at"),
            enriched_data=enriched_data,
            image=image,
            error_message=activity_dict.get("error_message")
        )
    
    @staticmethod
    def _create_enriched_nutrition_data(meal: Meal) -> Dict[str, Any]:
        """
        Create enriched nutrition data for a meal with nutrition information.
        
        Args:
            meal: Meal entity with nutrition data
            
        Returns:
            Dictionary containing enriched nutrition data
        """
        # Extract meal name from food items or use default
        meal_name = "Unknown Meal"
        if hasattr(meal.nutrition, 'food_items') and meal.nutrition.food_items:
            meal_name = meal.nutrition.food_items[0].name
        
        # Calculate weight (check for updated weight or use estimated)
        estimated_weight = 300.0  # Default weight
        if hasattr(meal, 'updated_weight_grams'):
            estimated_weight = meal.updated_weight_grams
        elif hasattr(meal.nutrition, 'food_items') and meal.nutrition.food_items:
            first_food = meal.nutrition.food_items[0]
            if first_food.unit and 'g' in first_food.unit.lower():
                estimated_weight = first_food.quantity
            elif first_food.quantity > 10:
                estimated_weight = first_food.quantity
        
        # Calculate nutrition values
        total_calories = meal.nutrition.calories
        if hasattr(meal, 'updated_weight_grams') and hasattr(meal, 'original_weight_grams'):
            ratio = meal.updated_weight_grams / meal.original_weight_grams
            total_calories = meal.nutrition.calories * ratio
        
        return {
            "meal_name": meal_name,
            "total_calories": round(total_calories, 1),
            "weight_grams": estimated_weight,
            "calories_per_100g": round((total_calories / estimated_weight) * 100, 1) if estimated_weight > 0 else 0,
            "macros": {
                "protein": round(meal.nutrition.macros.protein, 1),
                "carbs": round(meal.nutrition.macros.carbs, 1),
                "fat": round(meal.nutrition.macros.fat, 1),
                "fiber": round(meal.nutrition.macros.fiber, 1) if meal.nutrition.macros.fiber else None
            },
            "confidence_score": meal.nutrition.confidence_score,
            "food_items_count": len(meal.nutrition.food_items) if hasattr(meal.nutrition, 'food_items') and meal.nutrition.food_items else 0
        }
    
    @staticmethod
    def _create_basic_activity_data(meal: Meal) -> tuple[str, str]:
        """
        Create basic activity data for meals without nutrition information.
        
        Args:
            meal: Meal entity without nutrition
            
        Returns:
            Tuple of (title, description)
        """
        if meal.status == MealStatus.PROCESSING:
            return "Analyzing meal...", "AI is analyzing your meal image"
        elif meal.status == MealStatus.ANALYZING:
            return "Processing nutrition...", "Calculating nutritional information"
        elif meal.status == MealStatus.FAILED:
            return "Analysis failed", f"Unable to analyze meal: {meal.error_message or 'Unknown error'}"
        else:
            return "Meal scanned", "Meal has been processed"
    
    @staticmethod
    def _create_image_data(image) -> Dict[str, Any]:
        """
        Create image data dictionary from meal image.
        
        Args:
            image: Meal image object
            
        Returns:
            Image data dictionary
        """
        return {
            "image_id": image.image_id,
            "format": image.format,
            "size_bytes": image.size_bytes,
            "width": image.width,
            "height": image.height,
            "url": image.url if hasattr(image, 'url') else None
        } 
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Query

from api.schemas.activity_schemas import (
    ActivityResponse, ActivitiesListResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/activities",
    tags=["activities"],
)

@router.get("/", response_model=ActivitiesListResponse)
async def get_latest_activities(
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    start_date: Optional[str] = Query(None, description="Filter activities from this date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter activities until this date (ISO format)"),
    limit: int = Query(20, ge=1, le=100, description="Number of activities to return"),
    offset: int = Query(0, ge=0, description="Number of activities to skip"),
    # handler: ActivityHandler = Depends(get_activity_handler)
):
    """
    Retrieve all activities user done including food results after scanning or manually adding.
    
    This should be scalable as we will include the training or scan body on this 
    latest activity section later on.
    
    - Must priority endpoint
    - Returns paginated list of user activities
    - Includes meal scans, manual food additions, food updates, etc.
    """
    try:
        # TODO: Implement activity retrieval with filtering and pagination
        logger.info(f"Retrieving activities with filters: type={activity_type}, limit={limit}, offset={offset}")
        
        # Placeholder response - implement actual retrieval
        activities = [
            ActivityResponse(
                activity_id="activity-1",
                user_id=None,  # Will be populated when user system is implemented
                activity_type="MEAL_SCAN",
                title="Scanned meal with 3 items",
                description="Identified: Chicken Breast, Rice, Broccoli",
                metadata={
                    "meal_id": "meal-123",
                    "food_names": ["Chicken Breast", "Rice", "Broccoli"],
                    "food_count": 3,
                    "total_calories": 450
                },
                created_at="2024-01-01T12:30:00Z"
            ),
            ActivityResponse(
                activity_id="activity-2",
                user_id=None,
                activity_type="MANUAL_FOOD_ADD",
                title="Added Protein Shake manually",
                description="Manually added food item: Protein Shake",
                metadata={
                    "food_id": "food-456",
                    "food_name": "Protein Shake",
                    "calories": 120
                },
                created_at="2024-01-01T10:15:00Z"
            ),
            ActivityResponse(
                activity_id="activity-3",
                user_id=None,
                activity_type="FOOD_UPDATE",
                title="Updated Oatmeal",
                description="Updated fields: serving_size, calories",
                metadata={
                    "food_id": "food-789",
                    "food_name": "Oatmeal",
                    "updated_fields": ["serving_size", "calories"]
                },
                created_at="2024-01-01T08:00:00Z"
            ),
            ActivityResponse(
                activity_id="activity-4",
                user_id=None,
                activity_type="MACRO_CALCULATION",
                title="Daily macros calculated",
                description="Generated personalized macro targets",
                metadata={
                    "target_calories": 2000,
                    "target_protein": 150,
                    "target_carbs": 200,
                    "target_fat": 67
                },
                created_at="2024-01-01T07:00:00Z"
            )
        ]
        
        # Apply filtering based on activity_type if provided
        if activity_type:
            activities = [a for a in activities if a.activity_type == activity_type.upper()]
        
        # Apply pagination
        total_count = len(activities)
        paginated_activities = activities[offset:offset + limit]
        
        # Calculate total pages
        total_pages = (total_count + limit - 1) // limit
        current_page = (offset // limit) + 1
        
        return ActivitiesListResponse(
            activities=paginated_activities,
            total_count=total_count,
            page=current_page,
            page_size=limit,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error retrieving activities: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving activities: {str(e)}"
        )

@router.get("/types", response_model=List[str])
async def get_activity_types():
    """
    Get available activity types for filtering.
    
    - Returns list of available activity types
    """
    try:
        # Return available activity types
        return [
            "MEAL_SCAN",
            "MANUAL_FOOD_ADD", 
            "FOOD_UPDATE",
            "INGREDIENT_ADD",
            "MACRO_CALCULATION"
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving activity types: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving activity types: {str(e)}"
        )

@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: str,
    # handler: ActivityHandler = Depends(get_activity_handler)
):
    """
    Get specific activity details by ID.
    
    - Returns detailed information about a specific activity
    """
    try:
        # TODO: Implement specific activity retrieval
        logger.info(f"Retrieving activity: {activity_id}")
        
        # Placeholder response - implement actual retrieval
        return ActivityResponse(
            activity_id=activity_id,
            user_id=None,
            activity_type="MEAL_SCAN",
            title="Scanned meal with 2 items",
            description="Identified: Salmon, Quinoa",
            metadata={
                "meal_id": "meal-456",
                "food_names": ["Salmon", "Quinoa"],
                "food_count": 2,
                "total_calories": 380,
                "confidence_scores": [0.92, 0.88]
            },
            created_at="2024-01-01T18:45:00Z"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving activity {activity_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving activity: {str(e)}"
        ) 
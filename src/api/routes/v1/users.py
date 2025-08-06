"""
Users API endpoints - Firebase integration for user management.
Handles user authentication sync, profile retrieval, and status management.
"""
from fastapi import APIRouter, Depends

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.schemas.request.user_requests import (
    UserSyncRequest,
    UserUpdateLastAccessedRequest
)
from src.api.schemas.response.user_responses import (
    UserSyncResponse,
    UserProfileResponse,
    UserStatusResponse,
    UserUpdateResponse,
    OnboardingCompletionResponse
)
from src.app.commands.user import CompleteOnboardingCommand
from src.app.commands.user.sync_user_command import (
    SyncUserCommand,
    UpdateUserLastAccessedCommand
)
from src.app.queries.user.get_user_by_firebase_uid_query import (
    GetUserByFirebaseUidQuery,
    GetUserOnboardingStatusQuery
)
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/users", tags=["Users"])


@router.post("/sync", response_model=UserSyncResponse)
async def sync_user_from_firebase(
    request: UserSyncRequest,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Sync user data from Firebase authentication.
    
    Creates a new user if they don't exist, or updates existing user data.
    This endpoint is called automatically when a user signs in through Firebase.
    
    - **firebase_uid**: Firebase user unique identifier
    - **email**: User email address
    - **phone_number**: User phone number (optional)
    - **display_name**: User display name from Firebase (optional)
    - **photo_url**: User profile photo URL (optional)
    - **provider**: Authentication provider (phone, google)
    """
    try:
        # Create sync command
        command = SyncUserCommand(
            firebase_uid=request.firebase_uid,
            email=request.email,
            phone_number=request.phone_number,
            display_name=request.display_name,
            photo_url=request.photo_url,
            provider=request.provider,
            username=request.username,
            first_name=request.first_name,
            last_name=request.last_name
        )
        
        # Send command
        result = await event_bus.send(command)
        
        # Map result to response
        user_data = result["user"]

        return UserSyncResponse(
            user=UserProfileResponse(**user_data),
            created=result["created"],
            updated=result["updated"],
            message=result["message"]
        )
        
    except Exception as e:
        raise handle_exception(e)


@router.get("/firebase/{firebase_uid}", response_model=UserProfileResponse)
async def get_user_by_firebase_uid(
    firebase_uid: str,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get user profile by Firebase UID.
    
    Retrieves complete user profile information using Firebase UID.
    This is the primary way to get user data after Firebase authentication.
    
    - **firebase_uid**: Firebase user unique identifier
    """
    try:
        # Create query
        query = GetUserByFirebaseUidQuery(firebase_uid=firebase_uid)
        
        # Send query
        result = await event_bus.send(query)
        
        # Return user profile response
        return UserProfileResponse(**result)
        
    except Exception as e:
        raise handle_exception(e)


@router.get("/firebase/{firebase_uid}/status", response_model=UserStatusResponse)
async def get_user_onboarding_status(
    firebase_uid: str,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get user's onboarding status by Firebase UID.
    
    Returns minimal user status information for onboarding flow decisions.
    Used by the mobile app to determine if user needs to complete onboarding.
    
    - **firebase_uid**: Firebase user unique identifier
    """
    try:
        # Create query
        query = GetUserOnboardingStatusQuery(firebase_uid=firebase_uid)
        
        # Send query
        result = await event_bus.send(query)
        
        # Return status response
        return UserStatusResponse(**result)
        
    except Exception as e:
        raise handle_exception(e)


@router.put("/firebase/{firebase_uid}/last-accessed", response_model=UserUpdateResponse)
async def update_user_last_accessed(
    firebase_uid: str,
    request: UserUpdateLastAccessedRequest,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Update user's last accessed timestamp.
    
    Updates the last_accessed field for activity tracking and analytics.
    Called periodically by the mobile app to track user engagement.
    
    - **firebase_uid**: Firebase user unique identifier
    - **last_accessed**: Timestamp of last access (optional, defaults to now)
    """
    try:
        # Create command
        command = UpdateUserLastAccessedCommand(
            firebase_uid=firebase_uid,
            last_accessed=request.last_accessed
        )
        
        # Send command
        result = await event_bus.send(command)
        
        # Return update response
        return UserUpdateResponse(**result)
        
    except Exception as e:
        raise handle_exception(e)


@router.put("/firebase/{firebase_uid}/onboarding/complete", response_model=OnboardingCompletionResponse)
async def complete_onboarding(
    firebase_uid: str,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Mark user onboarding as completed.
    
    Sets the user's onboarding status to completed if it's currently false.
    This endpoint is called when the user finishes the onboarding flow in the mobile app.
    
    - **firebase_uid**: Firebase user unique identifier
    """
    try:
        # Create command
        command = CompleteOnboardingCommand(firebase_uid=firebase_uid)
        
        # Send command
        result = await event_bus.send(command)
        
        # Return completion response
        return OnboardingCompletionResponse(**result)
        
    except Exception as e:
        raise handle_exception(e)
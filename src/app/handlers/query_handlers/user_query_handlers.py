"""
DEPRECATED: Backward compatibility shim.

All handlers extracted to individual files:
- GetUserProfileQueryHandler → get_user_profile_query_handler.py
- GetUserByFirebaseUidQueryHandler → get_user_by_firebase_uid_query_handler.py
- GetUserOnboardingStatusQueryHandler → get_user_onboarding_status_query_handler.py

Please import from individual files or from the module.
"""
from .get_user_profile_query_handler import GetUserProfileQueryHandler
from .get_user_by_firebase_uid_query_handler import GetUserByFirebaseUidQueryHandler
from .get_user_onboarding_status_query_handler import GetUserOnboardingStatusQueryHandler

__all__ = [
    "GetUserProfileQueryHandler",
    "GetUserByFirebaseUidQueryHandler",
    "GetUserOnboardingStatusQueryHandler"
]

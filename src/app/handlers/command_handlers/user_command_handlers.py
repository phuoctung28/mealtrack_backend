"""
DEPRECATED: Backward compatibility shim.

All handlers extracted to individual files:
- SaveUserOnboardingCommandHandler → save_user_onboarding_command_handler.py
- SyncUserCommandHandler → sync_user_command_handler.py
- UpdateUserLastAccessedCommandHandler → update_user_last_accessed_command_handler.py
- CompleteOnboardingCommandHandler → complete_onboarding_command_handler.py

Please import from individual files or from the module.
"""
from .complete_onboarding_command_handler import CompleteOnboardingCommandHandler
from .save_user_onboarding_command_handler import SaveUserOnboardingCommandHandler
from .sync_user_command_handler import SyncUserCommandHandler
from .update_user_last_accessed_command_handler import UpdateUserLastAccessedCommandHandler

__all__ = [
    "SaveUserOnboardingCommandHandler",
    "SyncUserCommandHandler",
    "UpdateUserLastAccessedCommandHandler",
    "CompleteOnboardingCommandHandler"
]

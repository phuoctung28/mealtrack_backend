"""
DEPRECATED: Backward compatibility shim.

All handlers extracted to individual files:
- StartMealPlanConversationCommandHandler → start_meal_plan_conversation_command_handler.py
- SendConversationMessageCommandHandler → send_conversation_message_command_handler.py
- ReplaceMealInPlanCommandHandler → replace_meal_in_plan_command_handler.py
- GenerateDailyMealPlanCommandHandler → generate_daily_meal_plan_command_handler.py

Please import from individual files or from the module.
"""
from .generate_daily_meal_plan_command_handler import GenerateDailyMealPlanCommandHandler
from .replace_meal_in_plan_command_handler import ReplaceMealInPlanCommandHandler
from .send_conversation_message_command_handler import SendConversationMessageCommandHandler
from .start_meal_plan_conversation_command_handler import StartMealPlanConversationCommandHandler

__all__ = [
    "StartMealPlanConversationCommandHandler",
    "SendConversationMessageCommandHandler",
    "ReplaceMealInPlanCommandHandler",
    "GenerateDailyMealPlanCommandHandler"
]

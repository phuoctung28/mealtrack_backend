"""Conversation response formatting logic."""
from typing import List

from src.domain.model.meal_planning_wizard import ConversationContext


class ConversationFormatter:
    """Formats conversation responses."""

    @staticmethod
    def format_list(items: List[str]) -> str:
        """Format a list for display."""
        if not items:
            return "none"
        elif len(items) == 1:
            return items[0]
        else:
            return ", ".join(items[:-1]) + f" and {items[-1]}"

    @staticmethod
    def build_preferences_summary(context: ConversationContext) -> str:
        """Build a summary of user preferences."""
        duration = "weekly" if (context.plan_duration or "weekly") == "weekly" else "daily"
        dietary = ConversationFormatter.format_list(context.dietary_preferences or ["none"])

        summary = (f"You want a {duration}, {dietary} **meal plan** "
                  f"with {context.meals_per_day} meals")

        if context.snacks_per_day:
            summary += f" and {context.snacks_per_day} snacks"

        summary += f" per day. "

        if context.fitness_goal:
            summary += f"Your goal is {context.fitness_goal.replace('_', ' ')}. "

        summary += (f"You have ~{context.cooking_time_weekday} minutes to cook on weeknights, "
                   f"more on weekends.")

        if context.favorite_cuisines:
            summary += f" You enjoy {ConversationFormatter.format_list(context.favorite_cuisines)} foods"

        if context.disliked_ingredients:
            summary += f", and we'll avoid {ConversationFormatter.format_list(context.disliked_ingredients)}"

        if context.allergies:
            summary += f". You're allergic to {ConversationFormatter.format_list(context.allergies)}"

        summary += "."

        return summary

    @staticmethod
    def format_meal_plan_response(*args, **kwargs) -> str:
        """Legacy helper kept for backward compatibility; no longer used."""
        return (
            "Detailed weekly meal-plan rendering is currently disabled. "
            "Please use daily meal suggestions for concrete meal recommendations."
        )

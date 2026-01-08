"""Conversation response formatting logic."""
from typing import List

from src.domain.model.conversation import ConversationContext
from src.domain.model.meal_planning import MealPlan, MealType, PlanDuration


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
        duration = "weekly" if context.plan_duration == PlanDuration.WEEKLY.value else "daily"
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
    def format_meal_plan_response(meal_plan: MealPlan) -> str:
        """Format meal plan for display."""
        response = "Here's your **meal plan for the week**. I've organized it by day, with each meal tailored to your preferences and goals:\n\n"

        for day in meal_plan.days[:2]:  # Show first 2 days as example
            response += f"**{day.date.strftime('%A')}**\n\n"

            for meal in day.meals:
                response += f"* **{meal.meal_type.value.capitalize()}:** {meal.name} – *{meal.description}*"
                if meal.meal_type != MealType.SNACK:
                    response += f" (prep time ~{meal.total_time} min)"
                response += ".\n"

            response += "\n"

        response += ("*(...and similar meal listings for the rest of the week, "
                    "each meeting your dietary requirements and fitness goals...)*\n\n")

        response += ("I've kept the recipes **simple for busy weekdays** and included some of your favorite flavors "
                    "throughout the week. Each meal is tailored to your requirements and goals. "
                    "Let me know if anything doesn't look right or if you'd like to **adjust any specific meal**! 😊")

        return response

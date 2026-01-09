"""Conversation input parsing logic."""

import re
from typing import List, Tuple

from src.domain.model.meal_planning import FitnessGoal, PlanDuration


class ConversationParser:
    """Parses user input in conversations."""

    @staticmethod
    def parse_dietary_preferences(message: str) -> List[str]:
        """Parse dietary preferences from user message."""
        message_lower = message.lower()
        preferences = []

        preference_keywords = {
            "vegan": ["vegan"],
            "vegetarian": ["vegetarian"],
            "gluten_free": ["gluten-free", "gluten free", "celiac"],
            "keto": ["keto", "ketogenic"],
            "paleo": ["paleo"],
            "low_carb": ["low-carb", "low carb"],
            "dairy_free": ["dairy-free", "dairy free", "lactose"],
            "pescatarian": ["pescatarian", "fish"],
        }

        for pref, keywords in preference_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                preferences.append(pref)

        if not preferences and ("none" in message_lower or "no" in message_lower):
            preferences.append("none")

        return preferences if preferences else ["none"]

    @staticmethod
    def parse_allergies(message: str) -> List[str]:
        """Parse allergies from user message."""
        message_lower = message.lower()

        if "no" in message_lower or "none" in message_lower:
            return []

        # Common allergens
        allergens = [
            "nuts",
            "peanuts",
            "shellfish",
            "fish",
            "eggs",
            "milk",
            "dairy",
            "soy",
            "wheat",
            "gluten",
            "sesame",
            "tree nuts",
        ]

        found_allergies = []
        for allergen in allergens:
            if allergen in message_lower:
                found_allergies.append(allergen)

        return found_allergies

    @staticmethod
    def parse_fitness_goal(message: str) -> str:
        """Parse fitness goal from user message."""
        message_lower = message.lower()

        if (
            "muscle" in message_lower
            or "gain" in message_lower
            or "bulk" in message_lower
        ):
            return FitnessGoal.BULK.value
        elif (
            "loss" in message_lower or "lose" in message_lower or "cut" in message_lower
        ):
            return FitnessGoal.CUT.value
        elif (
            "recomp" in message_lower
            or "recomposition" in message_lower
            or "tone" in message_lower
        ):
            return FitnessGoal.RECOMP.value
        else:
            # Default to recomp (balanced approach)
            return FitnessGoal.RECOMP.value

    @staticmethod
    def parse_meal_count(message: str) -> Tuple[int, int]:
        """Parse meal and snack count from user message."""
        # Extract numbers from message
        numbers = re.findall(r"\d+", message)

        meals = 3  # default
        snacks = 0  # default

        if numbers:
            meals = int(numbers[0])
            if len(numbers) > 1:
                snacks = int(numbers[1])
            elif "snack" in message.lower():
                # If they mention snacks but only one number, assume 2 snacks
                snacks = 2

        # Reasonable limits
        meals = max(1, min(6, meals))
        snacks = max(0, min(4, snacks))

        return meals, snacks

    @staticmethod
    def parse_plan_duration(message: str) -> str:
        """Parse plan duration from user message."""
        message_lower = message.lower()

        if "week" in message_lower or "weekly" in message_lower:
            return PlanDuration.WEEKLY.value
        elif "day" in message_lower or "daily" in message_lower:
            return PlanDuration.DAILY.value
        else:
            # Default to weekly
            return PlanDuration.WEEKLY.value

    @staticmethod
    def parse_cooking_time(message: str) -> Tuple[int, int]:
        """Parse cooking time from user message."""
        # Extract numbers
        numbers = re.findall(r"\d+", message)

        weekday_time = 30  # default
        weekend_time = 60  # default

        if numbers:
            weekday_time = int(numbers[0])
            if len(numbers) > 1:
                weekend_time = int(numbers[1])
            else:
                # If only one time given, assume more time on weekends
                weekend_time = int(weekday_time * 1.5)

        return weekday_time, weekend_time

    @staticmethod
    def parse_cuisine_preferences(message: str) -> Tuple[List[str], List[str]]:
        """Parse cuisine preferences and dislikes from user message."""
        message_lower = message.lower()

        # Common cuisines
        cuisines = [
            "italian",
            "mexican",
            "asian",
            "chinese",
            "japanese",
            "thai",
            "indian",
            "mediterranean",
            "american",
            "french",
            "greek",
            "spanish",
        ]

        favorites = []
        for cuisine in cuisines:
            if cuisine in message_lower:
                favorites.append(cuisine.capitalize())

        # Parse dislikes
        dislikes = []
        if (
            "avoid" in message_lower
            or "don't like" in message_lower
            or "dislike" in message_lower
        ):
            # Simple parsing - in production, use NLP
            dislike_section = (
                message_lower.split("avoid")[-1]
                if "avoid" in message_lower
                else message_lower
            )

            # Common ingredients to check
            ingredients = [
                "tofu",
                "mushroom",
                "onion",
                "garlic",
                "spicy",
                "dairy",
                "egg",
            ]
            for ingredient in ingredients:
                if ingredient in dislike_section:
                    dislikes.append(ingredient)

        return favorites, dislikes

    @staticmethod
    def is_affirmative(message: str) -> bool:
        """Check if message is affirmative."""
        affirmative_words = [
            "yes",
            "yeah",
            "yep",
            "sure",
            "ok",
            "okay",
            "correct",
            "right",
            "sounds good",
            "perfect",
            "great",
        ]
        return any(word in message.lower() for word in affirmative_words)

    @staticmethod
    def is_negative(message: str) -> bool:
        """Check if message is negative."""
        negative_words = ["no", "nope", "not", "wrong", "incorrect", "bad"]
        return any(word in message.lower() for word in negative_words)

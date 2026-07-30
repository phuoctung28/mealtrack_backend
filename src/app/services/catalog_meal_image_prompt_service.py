"""Prompt construction for catalog meal image generation."""

from __future__ import annotations


def build_catalog_meal_image_prompt(meal) -> str:
    ingredients = ", ".join(
        str(item.display_name)
        for item in sorted(
            meal.ingredients,
            key=lambda ingredient: str(ingredient.display_name).lower(),
        )[:8]
    )
    cuisine = str(meal.cuisine).strip()
    name = str(meal.name).strip()
    ingredient_sentence = f" Visible ingredients: {ingredients}." if ingredients else ""
    return (
        f"Photorealistic editorial food photo of {name}, a {cuisine} meal."
        f"{ingredient_sentence} Single plated serving, natural daylight, clean table, "
        "appetizing realistic texture, no people, no packaging, no text, no logo, no watermark."
    )

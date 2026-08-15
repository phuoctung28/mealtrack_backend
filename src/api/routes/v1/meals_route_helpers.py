"""Shared helpers for meals route modules."""

from datetime import datetime

from src.api.exceptions import ValidationException
from src.api.schemas.response.meal_responses import ParsedFoodItem
from src.domain.model.nutrition.macros import Macros as MacrosModel


def parse_target_date(target_date: str | None):
    if not target_date:
        return None
    try:
        return datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValidationException(
            message="Invalid date format. Use YYYY-MM-DD format.",
            error_code="INVALID_DATE_FORMAT",
            details={"date": target_date},
        ) from e


def parsed_food_item_to_response(item) -> ParsedFoodItem:
    return ParsedFoodItem(
        name=item.name,
        quantity=item.quantity,
        unit=item.unit,
        calories=MacrosModel(
            protein=item.protein,
            carbs=item.carbs,
            fat=item.fat,
            fiber=item.fiber if hasattr(item, "fiber") and item.fiber else 0.0,
        ).total_calories,
        protein=item.protein,
        carbs=item.carbs,
        fat=item.fat,
        fiber=getattr(item, "fiber", 0.0) or 0.0,
        sugar=getattr(item, "sugar", 0.0) or 0.0,
        data_source=item.data_source,
        fdc_id=item.fdc_id,
        allowed_units=getattr(item, "allowed_units", None) or [],
    )

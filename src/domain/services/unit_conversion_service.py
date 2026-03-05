"""
Unit conversion service for converting food quantities between units.
"""
import logging
from typing import List, Optional

from src.domain.model.nutrition.serving_unit import ServingUnit

logger = logging.getLogger(__name__)


class UnitConversionService:
    """Service for converting food quantities to grams."""

    def convert_to_grams(
        self,
        quantity: float,
        unit: str,
        allowed_units: Optional[List[ServingUnit]] = None,
    ) -> float:
        """
        Convert quantity+unit to grams using food's allowed_units.

        Args:
            quantity: The amount in the given unit
            unit: The unit name (e.g., "cup", "tbsp", "g")
            allowed_units: List of allowed ServingUnits for the food

        Returns:
            The quantity in grams
        """
        # If already grams, return as-is
        if unit.lower() == "g":
            return quantity

        if not allowed_units:
            # Fallback: treat as grams (backward compat)
            logger.warning(f"No allowed_units provided, treating {quantity}{unit} as grams")
            return quantity

        # Try to find matching unit
        for su in allowed_units:
            if su.unit.lower() == unit.lower():
                return quantity * su.gram_weight

        # Unit not found in allowed_units - fallback to treating as grams
        logger.warning(
            f"Unit '{unit}' not found in allowed_units, treating {quantity} as grams"
        )
        return quantity

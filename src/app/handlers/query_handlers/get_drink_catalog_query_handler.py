"""
GetDrinkCatalogQueryHandler — returns the static in-process drink catalog.
No DB hit and no cache needed since the catalog lives in memory.
"""

from src.app.events.base import EventHandler, handles
from src.app.queries.hydration.get_drink_catalog_query import GetDrinkCatalogQuery
from src.domain.services.hydration_catalog_service import get_all


@handles(GetDrinkCatalogQuery)
class GetDrinkCatalogQueryHandler(EventHandler[GetDrinkCatalogQuery, dict]):
    """Handler for fetching the static drink catalog."""

    async def handle(self, query: GetDrinkCatalogQuery) -> dict:
        drinks = get_all()
        return {
            "drinks": [
                {
                    "id": d.id,
                    "name": d.name,
                    "sub": d.sub,
                    "emoji": d.emoji,
                    "default_ml": d.default_ml,
                    "kcal_per_100ml": d.kcal_per_100ml,
                    "sugar_per_100ml": d.sugar_per_100ml,
                    "hydration_weight": d.hydration_weight,
                    "brand_color": d.brand_color,
                    "category": d.category.value,
                }
                for d in drinks
            ]
        }

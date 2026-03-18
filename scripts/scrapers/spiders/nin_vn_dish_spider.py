"""
Spider: nin_vn_dishes
Target: https://viendinhduong.vn/en/cong-cu-va-tien-ich/nutritional-value-of-dishes

Scrapes cooked dish nutritional data (per 100g) from Vietnam NIN.
Inherits all parsing logic from NinVnFoodSpider; overrides source + URLs.
NOTE: Selectors are best-guess; verify against live site with browser DevTools.
"""

from .nin_vn_food_spider import NinVnFoodSpider


class NinVnDishSpider(NinVnFoodSpider):
    """Dish variant — same parsing, different start URL and source."""

    name = "nin_vn_dishes"
    source = "nin_vn"  # same source, dishes distinguished by category

    start_urls = [
        "https://viendinhduong.vn/en/cong-cu-va-tien-ich/nutritional-value-of-dishes"
    ]

    custom_settings = {
        "FEEDS": {
            "../../data/nin_vn_dishes.json": {
                "format": "json",
                "encoding": "utf-8",
                "overwrite": True,
            }
        }
    }

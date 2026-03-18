"""
Spider: nin_vn_foods
Target: https://viendinhduong.vn/en/cong-cu-va-tien-ich/nutritional-value-of-food

Scrapes raw food nutritional data (per 100g) from Vietnam National Institute
of Nutrition. Yields dicts matching common.schema.FoodEntry.

NOTE: Selectors are best-guess — verify against live site with browser DevTools.
      The site may use JS rendering; if so, enable scrapy-playwright in settings.
"""

import logging
from typing import Any, Generator

import scrapy
from scrapy.http import Response

from .nin_vn_helpers import build_column_map, row_to_entry

logger = logging.getLogger(__name__)


class NinVnFoodSpider(scrapy.Spider):
    name = "nin_vn_foods"
    start_urls = [
        "https://viendinhduong.vn/en/cong-cu-va-tien-ich/nutritional-value-of-food"
    ]
    # Subclass overrides
    source = "nin_vn"

    custom_settings = {
        "FEEDS": {
            "../../data/nin_vn_foods.json": {
                "format": "json",
                "encoding": "utf-8",
                "overwrite": True,
            }
        }
    }

    def parse(self, response: Response) -> Generator[Any, None, None]:
        """Entry point — detect food group tabs/links and follow each."""
        # TODO: Inspect actual nav structure in browser DevTools.
        # Pattern 1: category tabs as anchor links
        group_links = response.css(
            "ul.nav a[href], .tab-content a[href], .category-list a[href]"
        )

        if group_links:
            logger.info("Found %d food group links", len(group_links))
            for link in group_links:
                url = link.attrib.get("href", "")
                group_name = link.css("::text").get("").strip()
                if url:
                    yield response.follow(
                        url,
                        callback=self._parse_food_table,
                        cb_kwargs={"category_raw": group_name},
                    )
        else:
            # Pattern 2: table already on the main page
            logger.info("No group links — parsing table directly on %s", response.url)
            yield from self._parse_food_table(response, category_raw="Unknown")

    def _parse_food_table(
        self, response: Response, category_raw: str = "Unknown"
    ) -> Generator[dict, None, None]:
        """Parse a nutrition HTML table and yield one dict per food row."""
        # TODO: Adjust table selector after live inspection
        tables = response.css("table")

        if not tables:
            logger.warning("No table found on %s", response.url)
            return

        for table in tables:
            header_cells = table.css(
                "thead th, thead td, tr:first-child th, tr:first-child td"
            )
            headers = [h.css("::text").get("").strip() for h in header_cells]

            if len(headers) < 4:
                continue

            col_map = build_column_map(headers)
            logger.info("Category=%s | col_map=%s", category_raw, col_map)

            rows = table.css("tbody tr, tr:not(:first-child)")
            row_count = 0
            for row in rows:
                cells = [td.css("::text").get("").strip() for td in row.css("td")]
                if len(cells) < 3:
                    continue
                entry = row_to_entry(cells, col_map, category_raw, self.source)
                if entry:
                    row_count += 1
                    yield entry

            logger.info(
                "Yielded %d rows from %s (category=%s)",
                row_count, response.url, category_raw,
            )

        # Pagination: look for "next" link
        # TODO: Verify pagination selector from live site
        next_page = response.css(
            "a.next::attr(href), a[rel='next']::attr(href), "
            ".pagination .next a::attr(href)"
        ).get()
        if next_page:
            logger.info("Following pagination: %s", next_page)
            yield response.follow(
                next_page,
                callback=self._parse_food_table,
                cb_kwargs={"category_raw": category_raw},
            )

"""
Query to search foods via the configured manual logging provider.
"""

from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class SearchFoodsQuery(Query):
    query: str
    limit: int = 20
    language: str = "en"
    autocomplete: bool = False

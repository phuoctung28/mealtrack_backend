"""
Query to search foods via external database (USDA FDC).
"""
from dataclasses import dataclass
from src.app.events.base import Query


@dataclass
class SearchFoodsQuery(Query):
    query: str
    limit: int = 20

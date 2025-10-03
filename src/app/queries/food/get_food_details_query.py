"""
Query to get detailed nutrition by FDC ID.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetFoodDetailsQuery(Query):
    fdc_id: int

"""
Query to lookup product by barcode from OpenFoodFacts.
"""

from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class LookupBarcodeQuery(Query):
    barcode: str
    language: str = "en"

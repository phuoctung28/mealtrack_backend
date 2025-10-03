"""
USDA FoodData Central HTTP client. Real implementation would call external API; this is a thin wrapper.
"""
import os
from typing import Dict, Any, List, Optional

import requests

from src.domain.ports.food_data_service_port import FoodDataServicePort


class FoodDataService(FoodDataServicePort):
    BASE_URL = "https://api.nal.usda.gov/fdc/v1"

    def __init__(self, api_key: Optional[str] = None, session: Optional[requests.Session] = None):
        self.api_key = api_key or os.getenv("USDA_FDC_API_KEY", "")
        self.session = session or requests.Session()

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params = {**params, "api_key": self.api_key}
        resp = self.session.get(f"{self.BASE_URL}{path}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    async def search_foods(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        # For simplicity in tests, this won't be called. Kept for completeness.
        data = self._get("/foods/search", {"query": query, "pageSize": limit})
        return data.get("foods", [])

    async def get_food_details(self, fdc_id: int) -> Dict[str, Any]:
        return self._get(f"/food/{fdc_id}", {})

    async def get_multiple_foods(self, fdc_ids: List[int]) -> List[Dict[str, Any]]:
        # Batch endpoint; many accounts need POST. To keep simple, call individually.
        return [await self.get_food_details(fid) for fid in fdc_ids]

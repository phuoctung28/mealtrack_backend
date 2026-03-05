"""
FatSecret API HTTP client.
Provides product lookup by barcode and food search using OAuth 2.0.
"""
from typing import Dict, Any, Optional, List
import logging
import time
import base64
import re

import httpx

from src.infra.config.settings import settings

logger = logging.getLogger(__name__)

# FatSecret API endpoints
FATSECRET_TOKEN_URL = "https://oauth.fatsecret.com/connect/token"
FATSECRET_API_BASE = "https://platform.fatsecret.com/rest/v1"

# Barcode validation pattern (8-14 digits)
BARCODE_PATTERN = re.compile(r'^\d{8,14}$')


class FatSecretService:
    """HTTP client for FatSecret API with OAuth 2.0."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _get_access_token(self) -> Optional[str]:
        """Get OAuth 2.0 access token, refreshing if needed."""
        # Check if token is still valid (with 60s buffer)
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        # Get new token
        try:
            credentials = f"{self.client_id}:{self.client_secret}"
            b64_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Authorization": f"Basic {b64_credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            data = {"grant_type": "client_credentials"}

            client = await self._get_client()
            response = await client.post(
                FATSECRET_TOKEN_URL, headers=headers, data=data
            )

            if response.status_code != 200:
                logger.warning(
                    f"FatSecret token request failed: {response.status_code} - {response.text[:200]}"
                )
                return None

            token_data = response.json()
            self._access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = time.time() + expires_in

            return self._access_token
        except Exception as e:
            logger.warning(f"FatSecret OAuth error: {e}")
            return None

    async def _api_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make authenticated API request."""
        token = await self._get_access_token()
        if not token:
            return None

        url = f"{FATSECRET_API_BASE}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            client = await self._get_client()
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, params=params)
            else:
                response = await client.post(url, headers=headers, json=params)

            if response.status_code != 200:
                logger.warning(
                    f"FatSecret API error: {response.status_code} - {response.text[:200]}"
                )
                return None

            return response.json()
        except httpx.HTTPError as e:
            logger.warning(f"FatSecret request error: {e}")
            return None

    async def get_product(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Fetch product by barcode from FatSecret."""
        # Validate barcode format
        if not BARCODE_PATTERN.match(barcode):
            logger.warning(f"Invalid barcode format: {barcode}")
            return None

        try:
            normalized_barcode = barcode.zfill(13)
            params = {
                "method": "food.find_id_for_barcode",
                "barcode": normalized_barcode,
                "format": "json",
            }
            result = await self._api_request("GET", "", params)
            if not result:
                return None

            food_id = result.get("food_id")
            if not food_id:
                return None

            # Get food details
            detail_params = {"method": "food.get", "food_id": food_id, "format": "json"}
            food_details = await self._api_request("GET", "", detail_params)
            if not food_details:
                return None

            return self._map_product(food_details, normalized_barcode)
        except Exception as e:
            logger.warning(f"FatSecret API error for barcode {barcode}: {e}")
            return None

    async def search_foods(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search foods by query string with nutrition data."""
        try:
            params = {
                "method": "foods.search",
                "search_expression": query,
                "max_results": max_results,
                "page_number": 1,
                "format": "json",
            }
            result = await self._api_request("GET", "", params)
            if not result:
                return []

            foods = result.get("foods", {}).get("food", [])
            if not foods:
                return []
            if isinstance(foods, dict):
                foods = [foods]

            # Process each food with nutrition data
            processed = []
            for food in foods:
                food_id = food.get("food_id")
                mapped = self._map_search_result(food)

                # Fetch detailed nutrition if we have a food_id
                if food_id:
                    try:
                        detail_params = {"method": "food.get", "food_id": food_id, "format": "json"}
                        details = await self._api_request("GET", "", detail_params)
                        if details:
                            # Merge nutrition data
                            nutrition = self._extract_nutrition_from_details(details)
                            mapped.update(nrition)
                    except Exception:
                        pass  # Use basic mapped data if details fail

                processed.append(mapped)

            return processed
        except Exception as e:
            logger.warning(f"FatSecret search error for query '{query}': {e}")
            return []

    def _extract_nutrition_from_details(self, food: Dict[str, Any]) -> Dict[str, Any]:
        """Extract per-100g nutrition from FatSecret food details."""
        servings = food.get("servings", {}).get("serving", [])
        serving = None
        if isinstance(servings, list) and servings:
            serving = servings[0]
        elif isinstance(servings, dict):
            serving = servings

        if not isinstance(serving, dict):
            return {}

        # Get metric serving amount for per-100g calculation
        metric_amount = self._safe_float(serving.get("metric_serving_amount")) or 100

        return {
            "calories_100g": self._calc_per_100g(serving.get("calories"), metric_amount),
            "protein_100g": self._calc_per_100g(serving.get("protein"), metric_amount),
            "carbs_100g": self._calc_per_100g(serving.get("carbohydrate"), metric_amount),
            "fat_100g": self._calc_per_100g(serving.get("fat"), metric_amount),
            "serving_description": serving.get("serving_description"),
        }

    def _map_product(self, food: Dict[str, Any], barcode: str) -> Dict[str, Any]:
        """Map FatSecret response to clean dict."""
        servings = food.get("servings", {}).get("serving", [])
        serving = None
        if isinstance(servings, list) and servings:
            serving = servings[0]
        elif isinstance(servings, dict):
            serving = servings
        if not isinstance(serving, dict):
            return {
                "name": food.get("food_name", ""),
                "brand": food.get("brand_name"),
                "barcode": barcode,
                "calories_100g": None,
                "protein_100g": None,
                "carbs_100g": None,
                "fat_100g": None,
                "serving_size": None,
                "image_url": None,
            }
        # Use metric_serving_amount for accurate per-100g calculation
        metric_amount = self._safe_float(serving.get("metric_serving_amount")) or 100
        return {
            "name": food.get("food_name", ""),
            "brand": food.get("brand_name"),
            "barcode": barcode,
            "calories_100g": self._calc_per_100g(serving.get("calories"), metric_amount),
            "protein_100g": self._calc_per_100g(serving.get("protein"), metric_amount),
            "carbs_100g": self._calc_per_100g(serving.get("carbohydrate"), metric_amount),
            "fat_100g": self._calc_per_100g(serving.get("fat"), metric_amount),
            "serving_size": serving.get("serving_description"),
            "image_url": food.get("food_url"),
        }

    def _calc_per_100g(self, value: Any, metric_amount: float) -> Optional[float]:
        """Calculate nutrition value per 100g using metric_serving_amount."""
        if value is None:
            return None
        raw_value = self._safe_float(value)
        if raw_value is None:
            return None
        if metric_amount <= 0:
            return None
        return (raw_value / metric_amount) * 100

    def _map_search_result(self, food: Dict[str, Any]) -> Dict[str, Any]:
        """Map FatSecret search result to clean dict."""
        return {
            "description": food.get("food_name", ""),
            "brand": food.get("brand_name"),
            "food_description": food.get("food_description", ""),
            "source": "fatsecret",
            "food_id": food.get("food_id"),  # FatSecret's internal ID for getting details
        }

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


_fat_secret_service: Optional[FatSecretService] = None


def get_fat_secret_service() -> FatSecretService:
    """Get singleton instance of FatSecretService."""
    global _fat_secret_service
    if _fat_secret_service is None:
        # Use OAuth 2.0 credentials if available, otherwise fall back to OAuth 1.0
        client_id = settings.FATSECRET_CLIENT_ID
        client_secret = settings.FATSECRET_CLIENT_SECRET

        if not client_id or not client_secret:
            # Fall back to OAuth 1.0 (legacy)
            logger.warning(
                "FatSecret OAuth 2.0 credentials not configured, OAuth 1.0 not supported"
            )
            raise ValueError(
                "FATSECRET_CLIENT_ID and FATSECRET_CLIENT_SECRET must be set for OAuth 2.0"
            )

        _fat_secret_service = FatSecretService(
            client_id=client_id,
            client_secret=client_secret,
        )
    return _fat_secret_service

"""
Foods API routes: search and details via USDA, barcode lookup via OpenFoodFacts.

Uses a lightweight singleton event bus to avoid re-initializing
heavy services (Cloudinary, AI providers, etc.) on every request.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_food_search_event_bus
from src.api.middleware.accept_language import get_request_language
from src.api.schemas.response.barcode_product_response import BarcodeProductResponse
from src.app.queries.food.get_food_details_query import GetFoodDetailsQuery
from src.app.queries.food.lookup_barcode_query import LookupBarcodeQuery
from src.app.queries.food.search_foods_query import SearchFoodsQuery
from src.domain.exceptions.barcode_exceptions import InvalidBarcodeError
from src.domain.services.barcode import normalize_gtin

router = APIRouter(prefix="/v1/foods", tags=["Foods"])


@router.get("/search")
async def search_foods(
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
):
    """Search foods using lightweight singleton event bus."""
    event_bus = get_food_search_event_bus()
    language = get_request_language(request)
    query = SearchFoodsQuery(query=q, limit=limit, language=language)
    return await event_bus.send(query)


@router.get("/{fdc_id}/details")
async def get_food_details(
    fdc_id: int,
):
    """Get food details using lightweight singleton event bus."""
    event_bus = get_food_search_event_bus()
    query = GetFoodDetailsQuery(fdc_id=fdc_id)
    return await event_bus.send(query)


@router.get("/barcode/{barcode}", response_model=BarcodeProductResponse)
async def lookup_barcode(
    request: Request,
    barcode: str,
    user_id: str = Depends(get_current_user_id),
):
    """Look up product by barcode from structured providers and estimates."""
    event_bus = get_food_search_event_bus()
    language = get_request_language(request)
    try:
        lookup_keys = normalize_gtin(barcode)
    except InvalidBarcodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    query = LookupBarcodeQuery(
        barcode=lookup_keys.gtin_14,
        language=language,
        scanned_barcode=lookup_keys.raw,
        aliases=lookup_keys.aliases,
    )
    result = await event_bus.send(query)

    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return BarcodeProductResponse(**result)

"""App Store download redirect endpoint with campaign tracking."""

from urllib.parse import quote

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["app"])

APP_STORE_URL = "https://apps.apple.com/app/apple-store/id6751159552"


@router.get("/app-download")
async def app_download(source: str = Query(default="direct")):
    """
    Redirect to App Store with campaign tracking.

    Used as fallback when deep link fails or for direct download links.
    The `ct` parameter tracks which email/campaign drove the install.
    The `mt=8` parameter indicates iOS App Store.

    Args:
        source: Campaign source for tracking (e.g., "welcome_email", "email_footer")

    Returns:
        302 redirect to App Store with tracking params
    """
    return RedirectResponse(
        url=f"{APP_STORE_URL}?ct={quote(source, safe='')}&mt=8",
        status_code=302
    )

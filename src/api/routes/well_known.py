"""Apple App Site Association endpoint for Universal Links."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["well-known"])

# TODO: Replace with actual Apple Developer Team ID from App Store Connect
APPLE_TEAM_ID = "KB4Q9QGD7M"
APP_BUNDLE_ID = "com.nutreeai.mobile"


@router.get("/.well-known/apple-app-site-association")
async def apple_app_site_association():
    """
    Apple App Site Association file for Universal Links.

    This file tells iOS which URLs should open in the Nutree app
    instead of Safari. Apple crawls this within 24-48h of deployment.

    Requirements:
    - Must be served over HTTPS
    - Must return application/json content type
    - No redirects allowed on this path
    """
    return JSONResponse(
        content={
            "applinks": {
                "apps": [],
                "details": [{
                    "appID": f"{APPLE_TEAM_ID}.{APP_BUNDLE_ID}",
                    "paths": [
                        "/log",
                        "/log/*",
                        "/dashboard",
                        "/dashboard/*",
                        "/upgrade",
                        "/upgrade/*",
                        "/feedback",
                        "/feedback/*",
                        "/settings/*"
                    ]
                }]
            }
        },
        media_type="application/json"
    )

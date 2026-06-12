"""GET /v1/meals/upload-token — issue a short-lived Cloudinary signed-upload token."""

import logging
import uuid

from fastapi import APIRouter, Depends

from src.api.base_dependencies import get_image_store
from src.api.dependencies.auth import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/meals", tags=["Meals"])


@router.get("/upload-token")
async def get_upload_token(
    user_id: str = Depends(get_current_user_id),
    image_store=Depends(get_image_store),
):
    """Return a signed Cloudinary upload token. Client uploads directly; no bytes transit the backend."""
    image_id = str(uuid.uuid4())
    token = await image_store.generate_upload_signature_async(image_id)
    logger.info("[UPLOAD-TOKEN] user=%s image_id=%s", user_id, image_id)
    return token

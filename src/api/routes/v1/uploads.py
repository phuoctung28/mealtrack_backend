"""
Uploads API endpoints.
"""

from fastapi import APIRouter, Depends, status

from src.api.base_dependencies import get_image_store
from src.api.dependencies.auth import get_current_user_id
from src.api.exceptions import handle_exception
from src.api.schemas.response.meal_responses import UploadSignatureResponse
from src.domain.ports.image_store_port import ImageStorePort

router = APIRouter(prefix="/v1/uploads", tags=["Uploads"])


@router.post(
    "/sign",
    response_model=UploadSignatureResponse,
    status_code=status.HTTP_200_OK,
)
async def sign_upload(
    user_id: str = Depends(get_current_user_id),
    image_store: ImageStorePort = Depends(get_image_store),
) -> UploadSignatureResponse:
    """
    Generate signed params for direct Cloudinary upload.
    """
    try:
        _ = user_id  # auth required; user currently not embedded into public_id
        params = image_store.generate_upload_params()
        return UploadSignatureResponse(**params)
    except Exception as e:
        raise handle_exception(e) from e

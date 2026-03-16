from __future__ import annotations

import logging
import time
from typing import Any, Dict

import cloudinary.utils

from src.infra.config.settings import settings

logger = logging.getLogger(__name__)


class CloudinarySignatureService:
    """Generate signed parameters for direct client uploads to Cloudinary."""

    def __init__(self) -> None:
        if not settings.CLOUDINARY_CLOUD_NAME or not settings.CLOUDINARY_API_KEY or not settings.CLOUDINARY_API_SECRET:
            raise ValueError(
                "Cloudinary configuration is missing. "
                "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET."
            )

        self._cloud_name = settings.CLOUDINARY_CLOUD_NAME
        self._api_key = settings.CLOUDINARY_API_KEY
        self._api_secret = settings.CLOUDINARY_API_SECRET

    def generate_upload_signature(
        self,
        folder: str = "mealtrack",
        ttl_seconds: int = 600,
        extra_params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Generate a short-lived upload signature for client-side SDK usage.

        Args:
            folder: Cloudinary folder for uploaded assets.
            ttl_seconds: Time-to-live in seconds for the signature.
            extra_params: Additional upload params to include in the signature (e.g. allowed formats).

        Returns:
            Dict with api_key, cloud_name, timestamp, folder, signature.
        """
        timestamp = int(time.time())

        params: Dict[str, Any] = {
            "timestamp": timestamp,
            "folder": folder,
        }
        if extra_params:
            params.update(extra_params)

        signature = cloudinary.utils.api_sign_request(params_to_sign=params, api_secret=self._api_secret)

        logger.debug(
            "Generated Cloudinary upload signature (folder=%s, ttl=%s)",
            folder,
            ttl_seconds,
        )

        return {
            "cloud_name": self._cloud_name,
            "api_key": self._api_key,
            "timestamp": timestamp,
            "folder": folder,
            "signature": signature,
            # Extra params are returned so the client can send them as part of the upload body.
            "params": params,
            "expires_in": ttl_seconds,
        }


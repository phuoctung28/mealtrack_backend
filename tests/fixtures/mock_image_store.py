"""
Mock Image Store for testing.
"""
import uuid
from typing import Dict, Optional

from src.domain.ports.image_store_port import ImageStorePort


class MockImageStore(ImageStorePort):
    """Mock implementation of image store for testing."""
    
    def __init__(self):
        """Initialize with in-memory storage."""
        self.storage: Dict[str, bytes] = {}
    
    def save(self, image_bytes: bytes, content_type: str, image_id: Optional[str] = None) -> str:
        """Save image data and return image ID."""
        if image_id is None:
            image_id = str(uuid.uuid4())
        self.storage[image_id] = image_bytes
        return f"https://mock.cloudinary.com/images/{image_id}"

    def load(self, image_id: str) -> Optional[bytes]:
        """Load image data from storage."""
        # Extract ID from mock URL if needed
        if image_id.startswith("https://mock.cloudinary.com/images/"):
            image_id = image_id.replace("https://mock.cloudinary.com/images/", "")
        return self.storage.get(image_id)

    def delete(self, image_id: str) -> bool:
        """Delete image from storage."""
        if image_id in self.storage:
            del self.storage[image_id]
            return True
        return False

    def get_url(self, image_id: str) -> str:
        """Get mock URL for image."""
        return f"https://mock.cloudinary.com/images/{image_id}"

    async def save_async(
        self, image_bytes: bytes, content_type: str, image_id: Optional[str] = None
    ) -> str:
        return self.save(image_bytes, content_type, image_id)

    async def load_async(self, image_id: str) -> Optional[bytes]:
        return self.load(image_id)

    async def get_url_async(self, image_id: str) -> Optional[str]:
        return self.get_url(image_id)

    async def delete_async(self, image_id: str) -> bool:
        return self.delete(image_id)

    def generate_upload_signature(self, image_id: str, ttl: int = 300) -> dict:
        folder = "mealtrack"
        public_id = f"{folder}/{image_id}"
        return {
            "image_id": image_id,
            "cloud_name": "mock_cloud",
            "api_key": "mock_api_key",
            "timestamp": 1700000000,
            "signature": "mock_signature",
            "folder": folder,
            "public_id": public_id,
        }

    async def generate_upload_signature_async(self, image_id: str, ttl: int = 300) -> dict:
        return self.generate_upload_signature(image_id, ttl)
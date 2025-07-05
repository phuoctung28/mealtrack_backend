"""
Mock Image Store for testing.
"""
from typing import Dict, Optional
import uuid

from src.domain.ports.image_store_port import ImageStorePort


class MockImageStore(ImageStorePort):
    """Mock implementation of image store for testing."""
    
    def __init__(self):
        """Initialize with in-memory storage."""
        self.storage: Dict[str, bytes] = {}
    
    def save(self, image_data: bytes, content_type: str) -> str:
        """Save image data and return image ID."""
        image_id = str(uuid.uuid4())
        self.storage[image_id] = image_data
        return image_id
    
    def load(self, image_id: str) -> Optional[bytes]:
        """Load image data from storage."""
        # Extract ID from mock URL if needed
        if image_id.startswith("mock://images/"):
            image_id = image_id.replace("mock://images/", "")
        return self.storage.get(image_id)
    
    def delete(self, image_id: str) -> bool:
        """Delete image from storage."""
        if image_id in self.storage:
            del self.storage[image_id]
            return True
        return False
    
    def get_url(self, image_id: str) -> str:
        """Get mock URL for image."""
        return f"mock://images/{image_id}"
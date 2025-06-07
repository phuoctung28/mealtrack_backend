import os
import uuid
from typing import Optional, Dict
from dotenv import load_dotenv

from domain.ports.image_store_port import ImageStorePort

# Load environment variables if not already loaded
load_dotenv()

# For development/testing, can use a mock storage instead
USE_MOCK_STORAGE = bool(int(os.getenv("USE_MOCK_STORAGE", "1")))
UPLOAD_DIR = "uploads"

class ImageStore(ImageStorePort):
    """
    Implementation of ImageStorePort using a local file store for development.
    
    This class implements US-1.3 - Save the raw image bytes securely.
    """
    
    def __init__(self):
        """Initialize the image store."""
        if USE_MOCK_STORAGE and not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)
    
    def save(self, image_bytes: bytes, content_type: str) -> str:
        """
        Save image bytes to storage.
        
        Args:
            image_bytes: The raw bytes of the image
            content_type: MIME type of the image ("image/jpeg" or "image/png")
            
        Returns:
            A unique image ID (UUID string)
            
        Raises:
            ValueError: If content_type is not supported or image is invalid
        """
        # Validate content type
        if content_type not in ["image/jpeg", "image/png"]:
            raise ValueError(f"Unsupported content type: {content_type}")
        
        # Generate a deterministic UUID for the image
        image_id = str(uuid.uuid4())
        
        # For development, save locally
        extension = "jpg" if content_type == "image/jpeg" else "png"
        file_path = os.path.join(UPLOAD_DIR, f"{image_id}.{extension}")
        
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
        return image_id
    
    def load(self, image_id: str) -> Optional[bytes]:
        """
        Load image bytes by ID.
        
        Args:
            image_id: The ID of the image to load
            
        Returns:
            The raw bytes of the image if found, None otherwise
        """
        # Try both jpg and png extensions
        for ext in ["jpg", "png"]:
            file_path = os.path.join(UPLOAD_DIR, f"{image_id}.{ext}")
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    return f.read()
        return None
    
    def get_url(self, image_id: str) -> Optional[str]:
        """
        Gets a URL for accessing the image.
        
        Args:
            image_id: The ID of the image
            
        Returns:
            URL to access the image if available, None otherwise
        """
        # For local development, construct a path-based URL
        # This would typically point to a local development server
        for ext in ["jpg", "png"]:
            file_path = os.path.join(UPLOAD_DIR, f"{image_id}.{ext}")
            if os.path.exists(file_path):
                return f"/uploads/{image_id}.{ext}"
        return None
    
    def delete(self, image_id: str) -> bool:
        """
        Delete an image by ID.
        
        Args:
            image_id: The ID of the image to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        # Try to delete local file
        for ext in ["jpg", "png"]:
            file_path = os.path.join(UPLOAD_DIR, f"{image_id}.{ext}")
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        return False 
from abc import ABC, abstractmethod
from typing import Optional

class ImageStorePort(ABC):
    """Port interface for image storage operations."""
    
    @abstractmethod
    def save(self, image_bytes: bytes, content_type: str) -> str:
        """
        Saves image bytes to storage.
        
        Args:
            image_bytes: The raw bytes of the image
            content_type: MIME type of the image ("image/jpeg" or "image/png")
            
        Returns:
            A unique image ID (UUID string)
            
        Raises:
            ValueError: If content_type is not supported or image is invalid
        """
        pass
    
    @abstractmethod
    def load(self, image_id: str) -> Optional[bytes]:
        """
        Loads image bytes by ID.
        
        Args:
            image_id: The ID of the image to load
            
        Returns:
            The raw bytes of the image if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_url(self, image_id: str) -> Optional[str]:
        """
        Gets a URL for accessing the image, if applicable.
        
        Args:
            image_id: The ID of the image
            
        Returns:
            URL to access the image if available, None otherwise
        """
        pass
    
    @abstractmethod
    def delete(self, image_id: str) -> bool:
        """
        Deletes an image by ID.
        
        Args:
            image_id: The ID of the image to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass 
import os
import uuid
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils
from typing import Optional, Dict
from dotenv import load_dotenv
import logging

from domain.ports.image_store_port import ImageStorePort

# Load environment variables if not already loaded
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CloudinaryImageStore(ImageStorePort):
    """
    Implementation of ImageStorePort using Cloudinary cloud service.
    
    This class implements US-1.3 - Save the raw image bytes securely.
    """
    
    def __init__(self):
        """Initialize Cloudinary configuration."""
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")
        
        logger.info(f"Initializing CloudinaryImageStore with cloud_name: {cloud_name}")
        
        use_mock = bool(int(os.getenv("USE_MOCK_STORAGE", "1")))
        logger.info(f"USE_MOCK_STORAGE is set to: {use_mock}")
        
        if not all([cloud_name, api_key, api_secret]):
            raise ValueError("Missing Cloudinary configuration. Make sure CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET are set in .env file")
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret
        )
        
        logger.info("CloudinaryImageStore initialized successfully")
    
    def save(self, image_bytes: bytes, content_type: str) -> str:
        """
        Save image bytes to Cloudinary.
        
        Args:
            image_bytes: The raw bytes of the image
            content_type: MIME type of the image ("image/jpeg" or "image/png")
            
        Returns:
            A unique image ID (UUID string)
            
        Raises:
            ValueError: If content_type is not supported or image is invalid
        """
        logger.info(f"Saving image of type {content_type}, size {len(image_bytes)} bytes")
        
        # Validate content type
        if content_type not in ["image/jpeg", "image/png"]:
            raise ValueError(f"Unsupported content type: {content_type}")
        
        # Generate a UUID for the image
        image_id = str(uuid.uuid4())
        logger.info(f"Generated image_id: {image_id}")
        
        # Determine file extension from content type
        if content_type == "image/jpeg":
            file_extension = "jpg"
        elif content_type == "image/png":
            file_extension = "png"
        else:
            file_extension = "jpg"  # Default fallback
        
        # Upload to Cloudinary
        # Use the image_id with extension as the public_id in Cloudinary
        folder = "mealtrack"  # Use a folder for organization
        
        try:
            # Upload the image with explicit format
            logger.info(f"Uploading to Cloudinary with public_id: {folder}/{image_id}")
            response = cloudinary.uploader.upload(
                image_bytes,
                public_id=f"{folder}/{image_id}",
                resource_type="image",
                format=file_extension,  # Explicitly set the format
                overwrite=True
            )
            
            logger.info(f"Upload successful. Cloudinary URL: {response.get('secure_url')}")
            
            # Return the image ID
            return image_id
        except Exception as e:
            logger.error(f"Error uploading to Cloudinary: {str(e)}")
            raise
    
    def load(self, image_id: str) -> Optional[bytes]:
        """
        Load image bytes by ID from Cloudinary.
        
        Args:
            image_id: The ID of the image to load
            
        Returns:
            The raw bytes of the image if found, None otherwise
        """
        import requests
        
        logger.info(f"Loading image with ID: {image_id}")
        
        # Get the URL for the image
        url = self.get_url(image_id)
        
        if not url:
            logger.error(f"No URL found for image ID: {image_id}")
            return None
        
        # Fetch the image from Cloudinary
        try:
            logger.info(f"Fetching image from URL: {url}")
            response = requests.get(url)
            if response.status_code == 200:
                logger.info("Image successfully fetched")
                return response.content
            else:
                logger.error(f"Failed to fetch image. Status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching image: {str(e)}")
            pass
        
        return None
    
    def get_url(self, image_id: str) -> Optional[str]:
        """
        Gets a URL for accessing the image from Cloudinary.
        
        Args:
            image_id: The ID of the image
            
        Returns:
            URL to access the image if available, None otherwise
        """
        import requests
        
        logger.info(f"Getting URL for image ID: {image_id}")
        folder = "mealtrack"  # Same folder used in save method
        
        # Get cloud name from config
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        if not cloud_name:
            logger.error("CLOUDINARY_CLOUD_NAME not found in environment")
            return None
        
        # Try both common formats since we don't store the original format
        formats_to_try = ["jpg", "png"]
        
        for fmt in formats_to_try:
            # Build the direct Cloudinary URL
            # Format: https://res.cloudinary.com/{cloud_name}/image/upload/{folder}/{image_id}.{format}
            url = f"https://res.cloudinary.com/{cloud_name}/image/upload/{folder}/{image_id}.{fmt}"
            
            logger.info(f"Trying Cloudinary URL: {url}")
            
            # Check if the URL is accessible
            try:
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    logger.info(f"Found working URL: {url}")
                    return url
                else:
                    logger.debug(f"URL returned status {response.status_code}: {url}")
            except Exception as e:
                logger.debug(f"Error checking URL {url}: {str(e)}")
                continue
        
        logger.error(f"No working URL found for image ID: {image_id}")
        return None
    
    def delete(self, image_id: str) -> bool:
        """
        Delete an image by ID from Cloudinary.
        
        Args:
            image_id: The ID of the image to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        logger.info(f"Deleting image with ID: {image_id}")
        folder = "mealtrack"  # Same folder used in other methods
        
        try:
            # Delete the image from Cloudinary
            response = cloudinary.uploader.destroy(f"{folder}/{image_id}")
            success = response.get("result") == "ok"
            logger.info(f"Delete result: {success}")
            return success
        except Exception as e:
            logger.error(f"Error deleting image: {str(e)}")
            return False 
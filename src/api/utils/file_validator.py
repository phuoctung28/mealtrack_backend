"""
File validation utilities for API endpoints.
"""
from typing import List

from fastapi import UploadFile

from src.api.exceptions import ValidationException


class FileValidator:
    """Utility class for file validation."""
    
    @staticmethod
    async def validate_image_file(
        file: UploadFile,
        allowed_content_types: List[str],
        max_size_bytes: int
    ) -> bytes:
        """
        Validate an uploaded image file.
        
        Args:
            file: The uploaded file
            allowed_content_types: List of allowed MIME types
            max_size_bytes: Maximum file size in bytes
            
        Returns:
            The file contents as bytes
            
        Raises:
            ValidationException: If validation fails
        """
        # Validate content type
        if file.content_type not in allowed_content_types:
            raise ValidationException(
                f"Invalid file type '{file.content_type}'. "
                f"Allowed types: {', '.join(allowed_content_types)}"
            )
        
        # Read file contents
        contents = await file.read()
        
        # Validate file size
        if len(contents) > max_size_bytes:
            size_mb = max_size_bytes / (1024 * 1024)
            raise ValidationException(
                f"File size exceeds maximum allowed size of {size_mb}MB"
            )
        
        # Validate file is not empty
        if len(contents) == 0:
            raise ValidationException("File is empty")
        
        # Reset file position for potential reuse
        await file.seek(0)
        
        return contents
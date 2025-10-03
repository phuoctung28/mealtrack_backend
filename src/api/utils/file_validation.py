"""
File validation utilities for API endpoints.
"""
from typing import List

from fastapi import UploadFile

from src.api.exceptions import ValidationException


class FileValidator:
    """Validates uploaded files."""
    
    @staticmethod
    def validate_image_file(
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
            The file content as bytes
            
        Raises:
            ValidationException: If validation fails
        """
        # Validate content type
        if file.content_type not in allowed_content_types:
            raise ValidationException(
                message=f"Invalid file type. Only {', '.join(allowed_content_types)} are allowed.",
                error_code="INVALID_FILE_TYPE",
                details={"content_type": file.content_type, "allowed": allowed_content_types}
            )
        
        # Read file content
        try:
            contents = file.file.read()
        except Exception as e:
            raise ValidationException(
                message="Failed to read file content",
                error_code="FILE_READ_ERROR",
                details={"error": str(e)}
            )
        finally:
            file.file.seek(0)  # Reset file pointer
        
        # Validate file size
        if len(contents) > max_size_bytes:
            raise ValidationException(
                message=f"File size exceeds maximum allowed ({max_size_bytes // (1024*1024)}MB)",
                error_code="FILE_TOO_LARGE",
                details={"size_bytes": len(contents), "max_bytes": max_size_bytes}
            )
        
        return contents
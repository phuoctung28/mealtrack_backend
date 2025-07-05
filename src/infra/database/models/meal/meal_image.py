"""
Meal image model for storing image metadata.
"""
from sqlalchemy import Column, String, Integer

from src.infra.database.config import Base
from src.infra.database.models.base import TimestampMixin


class MealImage(Base, TimestampMixin):
    """Database model for meal images."""
    
    __tablename__ = 'mealimage'
    
    # Primary key
    image_id = Column(String(36), primary_key=True)
    format = Column(String(10), nullable=False)  # jpeg, png, etc.
    size_bytes = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)  # Changed to nullable
    height = Column(Integer, nullable=True)  # Changed to nullable
    url = Column(String(255), nullable=True)  # Optional URL to the image
    
    def to_domain(self):
        """Convert DB model to domain model."""
        from src.domain.model.meal_image import MealImage as DomainMealImage
        
        return DomainMealImage(
            image_id=self.image_id,
            format=self.format,
            size_bytes=self.size_bytes,
            width=self.width,
            height=self.height,
            url=self.url
        )
    
    @classmethod
    def from_domain(cls, domain_model):
        """Create DB model from domain model."""
        return cls(
            image_id=domain_model.image_id,
            format=domain_model.format,
            size_bytes=domain_model.size_bytes,
            width=getattr(domain_model, "width", None),
            height=getattr(domain_model, "height", None),
            url=getattr(domain_model, "url", None)
        )
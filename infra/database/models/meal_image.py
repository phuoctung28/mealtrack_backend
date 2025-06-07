from sqlalchemy import Column, String, Integer

from infra.database.config import Base
from infra.database.models.base import BaseMixin

class MealImage(Base, BaseMixin):
    """Database model for meal images."""
    
    # Rename primary key from 'id' to 'image_id' to match domain model
    image_id = Column(String(36), primary_key=True)
    format = Column(String(10), nullable=False)  # jpeg, png, etc.
    size_bytes = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)  # Changed to nullable
    height = Column(Integer, nullable=True)  # Changed to nullable
    url = Column(String(255), nullable=True)  # Optional URL to the image
    
    # Override to remove the default id column from BaseMixin
    id = None
    
    def to_domain(self):
        """Convert DB model to domain model."""
        from domain.model.meal_image import MealImage as DomainMealImage
        
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
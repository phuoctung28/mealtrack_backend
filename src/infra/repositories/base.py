"""
Base repository class for common database operations.
"""
from typing import TypeVar, Generic, Type, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import uuid4

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations."""
    
    def __init__(self, model_class: Type[T], session: Session):
        self.model_class = model_class
        self.session = session
    
    def get(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        return self.session.query(self.model_class).filter(
            self.model_class.id == id
        ).first()
    
    def get_all(self) -> List[T]:
        """Get all entities."""
        return self.session.query(self.model_class).all()
    
    def add(self, entity: T) -> T:
        """Add new entity."""
        if hasattr(entity, 'id') and not entity.id:
            entity.id = str(uuid4())
        self.session.add(entity)
        self.session.flush()
        return entity
    
    def update(self, entity: T) -> T:
        """Update entity."""
        self.session.add(entity)
        self.session.flush()
        return entity
    
    def delete(self, id: str) -> bool:
        """Delete entity by ID."""
        entity = self.get(id)
        if entity:
            self.session.delete(entity)
            self.session.flush()
            return True
        return False
    
    # Async wrappers for compatibility
    async def get_async(self, id: str) -> Optional[T]:
        """Async wrapper for get."""
        return self.get(id)
    
    async def add_async(self, entity: T) -> T:
        """Async wrapper for add."""
        return self.add(entity)
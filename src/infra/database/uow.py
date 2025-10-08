"""
Unit of Work pattern implementation for managing database transactions.
"""
from typing import Type, TypeVar
from sqlalchemy.orm import Session

from src.infra.repositories.user_repository import UserRepository
from src.infra.repositories.subscription_repository import SubscriptionRepository


T = TypeVar('T')


class UnitOfWork:
    """
    Unit of Work pattern for managing database transactions.
    
    Ensures all repository operations within a context are committed or rolled back together.
    """
    
    def __init__(self, session: Session = None):
        self.session = session
        
    def __enter__(self):
        """Enter context - start transaction."""
        if not self.session:
            # Default session handling - import here to avoid circular imports
            from src.infra.database.config import SessionLocal
            self.session = SessionLocal()
            
        # Initialize repositories
        self.users = UserRepository(self.session)
        self.subscriptions = SubscriptionRepository(self.session)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - commit or rollback transaction."""
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.session.close()
    
    async def __aenter__(self):
        """Support async context manager for compatibility."""
        return self.__enter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Support async context manager for compatibility."""
        return self.__exit__(exc_type, exc_val, exc_tb)
    
    def commit(self):
        """Commit the transaction."""
        self.session.commit()
    
    async def commit_async(self):
        """Async wrapper for commit."""
        self.commit()
    
    def rollback(self):
        """Rollback the transaction."""
        self.session.rollback()
    
    async def rollback_async(self):
        """Async wrapper for rollback."""
        self.rollback()
    
    def refresh(self, obj):
        """Refresh an object from the database."""
        self.session.refresh(obj)
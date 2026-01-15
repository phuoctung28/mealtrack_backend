"""
Chat repository implementation using SQLAlchemy.
"""
import json
import logging
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.model.chat import Thread, Message, ThreadStatus
from src.domain.ports.chat_repository_port import ChatRepositoryPort
from src.domain.services.timezone_utils import utc_now
from src.infra.database.models.chat import ChatThread, ChatMessage

logger = logging.getLogger(__name__)


class ChatRepository(ChatRepositoryPort):
    """SQL implementation of ChatRepositoryPort."""
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize repository with optional database session.
        
        If db is None, the repository will create its own session for each operation.
        If db is provided, the repository will use it and NOT manage its lifecycle.
        The session lifecycle should be managed by the caller (e.g., FastAPI dependency).
        """
        self.db = db
    
    def save_thread(self, thread: Thread) -> Thread:
        """Save a thread and return the saved thread."""
        # Use provided session or create one for this operation
        if self.db:
            db = self.db
        else:
            from src.infra.database.config import ScopedSession
            db = ScopedSession()
        
        try:
            # Check if thread exists
            existing = db.query(ChatThread).filter(ChatThread.id == thread.thread_id).first()
            
            if existing:
                # Update existing thread
                existing.title = thread.title
                existing.status = str(thread.status).lower()
                existing.is_active = thread.status == ThreadStatus.ACTIVE
                existing.updated_at = thread.updated_at
                
                if thread.metadata:
                    existing.metadata_ = json.dumps(thread.metadata)
                
                db_thread = existing
            else:
                # Create new thread
                db_thread = ChatThread(
                    id=thread.thread_id,
                    user_id=thread.user_id,
                    title=thread.title,
                    status=str(thread.status).lower(),
                    is_active=thread.status == ThreadStatus.ACTIVE,
                    metadata_=json.dumps(thread.metadata) if thread.metadata else None,
                    created_at=thread.created_at,
                    updated_at=thread.updated_at
                )
                db.add(db_thread)
            
            db.commit()
            db.refresh(db_thread)
            
            return db_thread.to_domain()
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving thread: {e}")
            raise e
        finally:
            # Only close if we created the session
            if not self.db:
                db.close()
    
    def find_thread_by_id(self, thread_id: str) -> Optional[Thread]:
        """Find a thread by its ID."""
        # Use provided session or create one for this operation
        if self.db:
            db = self.db
        else:
            from src.infra.database.config import ScopedSession
            db = ScopedSession()
        
        try:
            db_thread = db.query(ChatThread).filter(ChatThread.id == thread_id).first()
            
            if not db_thread:
                return None
            
            return db_thread.to_domain()
        
        finally:
            # Only close if we created the session
            if not self.db:
                db.close()
    
    def find_threads_by_user(
        self,
        user_id: str,
        include_deleted: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Thread]:
        """Find all threads for a user with pagination."""
        # Use provided session or create one for this operation
        if self.db:
            db = self.db
        else:
            from src.infra.database.config import ScopedSession
            db = ScopedSession()
        
        try:
            # Create subquery for message counts to avoid N+1 queries
            message_count_subquery = (
                db.query(func.count(ChatMessage.id))
                .filter(ChatMessage.thread_id == ChatThread.id)
                .correlate(ChatThread)
                .scalar_subquery()
            )
            
            query = db.query(
                ChatThread,
                message_count_subquery.label('message_count')
            ).filter(ChatThread.user_id == user_id)
            
            if not include_deleted:
                query = query.filter(ChatThread.status != 'deleted')
            
            query = query.order_by(ChatThread.updated_at.desc())
            query = query.limit(limit).offset(offset)
            
            results = query.all()
            
            # Convert to domain models with message counts
            threads = []
            for db_thread, message_count in results:
                domain_thread = db_thread.to_domain()
                # Cache message count to avoid N+1 queries when to_dict() calls get_message_count()
                # This allows get_message_count() to return the count without loading all messages
                object.__setattr__(domain_thread, '_cached_message_count', message_count or 0)
                threads.append(domain_thread)
            
            return threads
        
        finally:
            # Only close if we created the session
            if not self.db:
                db.close()
    
    def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread (soft delete)."""
        # Use provided session or create one for this operation
        if self.db:
            db = self.db
        else:
            from src.infra.database.config import ScopedSession
            db = ScopedSession()
        
        try:
            db_thread = db.query(ChatThread).filter(ChatThread.id == thread_id).first()
            
            if not db_thread:
                return False
            
            db_thread.status = 'deleted'
            db_thread.is_active = False
            db_thread.updated_at = utc_now()
            
            db.commit()
            return True
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting thread: {e}")
            raise e
        finally:
            # Only close if we created the session
            if not self.db:
                db.close()
    
    def save_message(self, message: Message) -> Message:
        """Save a message and return the saved message."""
        # Use provided session or create one for this operation
        if self.db:
            db = self.db
        else:
            from src.infra.database.config import ScopedSession
            db = ScopedSession()
        
        try:
            # Check if message exists
            existing = db.query(ChatMessage).filter(ChatMessage.id == message.message_id).first()
            
            if existing:
                # Update existing message (though messages should be immutable)
                existing.content = message.content
                if message.metadata:
                    existing.metadata_ = json.dumps(message.metadata)
                db_message = existing
            else:
                # Create new message
                db_message = ChatMessage(
                    id=message.message_id,
                    thread_id=message.thread_id,
                    role=str(message.role).lower(),
                    content=message.content,
                    metadata_=json.dumps(message.metadata) if message.metadata else None,
                    created_at=message.created_at
                )
                db.add(db_message)
            
            # Update thread's updated_at
            db_thread = db.query(ChatThread).filter(ChatThread.id == message.thread_id).first()
            if db_thread:
                db_thread.updated_at = utc_now()
            
            db.commit()
            db.refresh(db_message)
            
            return db_message.to_domain()
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving message: {e}")
            raise e
        finally:
            # Only close if we created the session
            if not self.db:
                db.close()
    
    def find_messages_by_thread(
        self,
        thread_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Message]:
        """Find all messages for a thread with pagination."""
        # Use provided session or create one for this operation
        if self.db:
            db = self.db
        else:
            from src.infra.database.config import ScopedSession
            db = ScopedSession()
        
        try:
            query = db.query(ChatMessage).filter(ChatMessage.thread_id == thread_id)
            query = query.order_by(ChatMessage.created_at.asc())
            query = query.limit(limit).offset(offset)
            
            db_messages = query.all()
            
            return [message.to_domain() for message in db_messages]
        
        finally:
            # Only close if we created the session
            if not self.db:
                db.close()
    
    def count_user_threads(self, user_id: str, include_deleted: bool = False) -> int:
        """Count total threads for a user."""
        # Use provided session or create one for this operation
        if self.db:
            db = self.db
        else:
            from src.infra.database.config import ScopedSession
            db = ScopedSession()
        
        try:
            query = db.query(func.count(ChatThread.id)).filter(ChatThread.user_id == user_id)
            
            if not include_deleted:
                query = query.filter(ChatThread.status != 'deleted')
            
            return query.scalar() or 0
        
        finally:
            # Only close if we created the session
            if not self.db:
                db.close()
    
    def count_thread_messages(self, thread_id: str) -> int:
        """Count total messages in a thread."""
        # Use provided session or create one for this operation
        if self.db:
            db = self.db
        else:
            from src.infra.database.config import ScopedSession
            db = ScopedSession()
        
        try:
            return db.query(func.count(ChatMessage.id)).filter(
                ChatMessage.thread_id == thread_id
            ).scalar() or 0
        
        finally:
            # Only close if we created the session
            if not self.db:
                db.close()


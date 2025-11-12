"""
Handler for getting list of threads for a user.
"""
import logging
from typing import Dict, Any

from src.app.events.base import EventHandler, handles
from src.app.queries.chat import GetThreadsQuery
from src.domain.ports.chat_repository_port import ChatRepositoryPort

logger = logging.getLogger(__name__)


@handles(GetThreadsQuery)
class GetThreadsQueryHandler(EventHandler[GetThreadsQuery, Dict[str, Any]]):
    """Handler for getting user's threads."""
    
    def __init__(self, chat_repository: ChatRepositoryPort = None):
        self.chat_repository = chat_repository
    
    def set_dependencies(self, chat_repository: ChatRepositoryPort):
        """Set dependencies for dependency injection."""
        self.chat_repository = chat_repository
    
    async def handle(self, query: GetThreadsQuery) -> Dict[str, Any]:
        """Get threads for a user."""
        if not self.chat_repository:
            raise RuntimeError("Chat repository not configured")
        
        # Get threads
        threads = self.chat_repository.find_threads_by_user(
            user_id=query.user_id,
            include_deleted=query.include_deleted,
            limit=query.limit,
            offset=query.offset
        )
        
        # Get total count
        total_count = self.chat_repository.count_user_threads(
            user_id=query.user_id,
            include_deleted=query.include_deleted
        )
        
        return {
            "threads": [thread.to_dict() for thread in threads],
            "total_count": total_count,
            "limit": query.limit,
            "offset": query.offset
        }


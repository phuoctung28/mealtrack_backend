"""
GetUserMetricsQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any, Optional

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import handles, EventHandler
from src.app.queries.user import GetUserMetricsQuery
from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.cache_port import CachePort
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)

@handles(GetUserMetricsQuery)
class GetUserMetricsQueryHandler(EventHandler[GetUserMetricsQuery, Dict[str, Any]]):
    """Handler for getting user's current metrics for settings display."""

    def __init__(self, cache_service: Optional[CachePort] = None):
        self.cache_service = cache_service

    async def handle(self, query: GetUserMetricsQuery) -> Dict[str, Any]:
        """Get user's current metrics."""
        cache_key, ttl = CacheKeys.user_metrics(query.user_id)
        if self.cache_service:
            cached = await self.cache_service.get_json(cache_key)
            if cached is not None:
                return cached
        result = await self._compute(query)
        if self.cache_service:
            await self.cache_service.set_json(cache_key, result, ttl)
        return result

    async def _compute(self, query: GetUserMetricsQuery) -> Dict[str, Any]:
        """Fetch user metrics from DB."""
        with UnitOfWork() as uow:
            # Get current user profile using the UnitOfWork session
            profile = (
                uow.session.query(UserProfile)
                .filter(
                    UserProfile.user_id == query.user_id,
                    UserProfile.is_current.is_(True),
                )
                .first()
            )

            if not profile:
                raise ResourceNotFoundException(f"Current profile for user {query.user_id} not found")

            return {
                "user_id": query.user_id,
                "age": profile.age,
                "gender": profile.gender,
                "height_cm": profile.height_cm,
                "weight_kg": profile.weight_kg,
                "body_fat_percentage": profile.body_fat_percentage,
                "job_type": profile.job_type,
                "training_days_per_week": profile.training_days_per_week,
                "training_minutes_per_session": profile.training_minutes_per_session,
                "training_level": profile.training_level,
                "fitness_goal": profile.fitness_goal,
                "target_weight_kg": profile.target_weight_kg,
                "updated_at": profile.updated_at,
            }
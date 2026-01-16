"""
GetUserMetricsQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import handles, EventHandler
from src.app.queries.user import GetUserMetricsQuery
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)

@handles(GetUserMetricsQuery)
class GetUserMetricsQueryHandler(EventHandler[GetUserMetricsQuery, Dict[str, Any]]):
    """Handler for getting user's current metrics for settings display."""

    async def handle(self, query: GetUserMetricsQuery) -> Dict[str, Any]:
        """Get user's current metrics."""
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
                "activity_level": profile.activity_level,
                "fitness_goal": profile.fitness_goal,
                "target_weight_kg": profile.target_weight_kg,
                "updated_at": profile.updated_at,
            }
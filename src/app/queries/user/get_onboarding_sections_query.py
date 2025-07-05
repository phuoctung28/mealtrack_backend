"""
Get onboarding sections query.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetOnboardingSectionsQuery(Query):
    """Query to get onboarding sections."""
    pass
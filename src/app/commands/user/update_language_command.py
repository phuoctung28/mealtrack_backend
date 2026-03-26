"""Command to update user language preference."""
from dataclasses import dataclass
from uuid import UUID

from src.app.events.base import Command


SUPPORTED_LANGUAGES = {'en', 'vi', 'es', 'fr', 'de', 'ja', 'zh'}


@dataclass
class UpdateLanguageCommand(Command):
    """Command to update user's preferred language."""
    user_id: UUID
    language_code: str  # ISO 639-1 code

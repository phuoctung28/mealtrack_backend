"""Command to update user language preference."""

from dataclasses import dataclass
from uuid import UUID

from src.app.events.base import Command
from src.domain.constants.languages import SUPPORTED_TRANSLATION_LANGUAGES

SUPPORTED_LANGUAGES = SUPPORTED_TRANSLATION_LANGUAGES


@dataclass
class UpdateLanguageCommand(Command):
    """Command to update user's preferred language."""

    user_id: UUID
    language_code: str  # ISO 639-1 code

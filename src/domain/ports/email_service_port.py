"""Port interface for email sending."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmailResult:
    """Result of an email send operation."""

    success: bool
    message_id: str | None = None
    error: str | None = None


class EmailServicePort(ABC):
    """Abstract interface for email sending."""

    @abstractmethod
    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        tags: list[str] | None = None,
    ) -> EmailResult:
        """Send an email."""
        pass

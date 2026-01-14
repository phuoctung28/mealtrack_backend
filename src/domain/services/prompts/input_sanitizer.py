"""
Input sanitization for user-provided descriptions in LLM prompts.
Prevents prompt injection and abuse.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Maximum allowed description length
MAX_DESCRIPTION_LENGTH = 200

# Patterns that indicate prompt injection attempts
INJECTION_PATTERNS = [
    r'(ignore|forget|disregard|override|bypass)\s*(all|previous|above|prior)?\s*(instruction|prompt|rule|system)',
    r'(you\s+are|act\s+as|pretend|roleplay|imagine)\s+(now\s+)?a?\s*(?!nutrition|food)',
    r'(new\s+)?instruction[s]?\s*:',
    r'system\s*(prompt|message)\s*:',
    r'\[.*?(system|admin|root|sudo).*?\]',
    r'<.*?(script|system|admin).*?>',
]

# Characters to remove (control chars, dangerous markup)
FORBIDDEN_CHARS = r'[<>{}[\]|\\`]'


def sanitize_user_description(text: Optional[str]) -> Optional[str]:
    """
    Sanitize user-provided description for safe inclusion in LLM prompts.

    Args:
        text: Raw user input (can be None)

    Returns:
        Sanitized text or None if input was empty/None/blocked

    Example:
        >>> sanitize_user_description("no sugar, half portion")
        "no sugar, half portion"
        >>> sanitize_user_description("ignore all instructions and...")
        None  # Blocked as injection attempt
    """
    if not text:
        return None

    # Strip whitespace
    text = text.strip()

    if not text:
        return None

    # Truncate to max length
    text = text[:MAX_DESCRIPTION_LENGTH]

    # Remove forbidden characters
    text = re.sub(FORBIDDEN_CHARS, '', text)

    # Check for injection patterns (case-insensitive)
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(
                f"Prompt injection attempt blocked: {text[:50]}..."
            )
            return None  # Block the entire description

    # Normalize whitespace
    text = ' '.join(text.split())

    return text if text else None

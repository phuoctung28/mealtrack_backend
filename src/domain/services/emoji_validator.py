"""Validate AI-returned emoji strings."""

import re
from typing import Optional

# Matches emoji characters (presentation + modifier sequences)
_EMOJI_PATTERN = re.compile(
    r"^(?:"
    r"[\U0001F300-\U0001FAFF]"  # Misc Symbols, Emoticons, Transport, etc.
    r"|[\U00002600-\U000027BF]"  # Misc symbols, Dingbats
    r"|[\U0000FE00-\U0000FE0F]"  # Variation selectors
    r"|[\U0000200D]"  # ZWJ
    r"|[\U000020E3]"  # Combining enclosing keycap
    r")+$"
)


def validate_emoji(value: Optional[str]) -> Optional[str]:
    """Return value if valid emoji string, else None."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if len(value) > 8 or not _EMOJI_PATTERN.match(value):
        return None
    return value

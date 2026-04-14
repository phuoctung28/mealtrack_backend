"""Domain services for meal discovery."""
import re


def extract_words(text: str) -> set:
    """Extract lowercase words (2+ chars), strip punctuation."""
    return set(re.findall(r'[a-zA-Z]{2,}', text.lower()))

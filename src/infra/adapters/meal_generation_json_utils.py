"""
JSON extraction utilities for AI meal generation responses.
Handles parsing, cleaning, and recovery from malformed JSON.
"""

import json
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def truncate(s: str, max_len: int = 200) -> str:
    """Truncate string for logging."""
    return s[:max_len] + "..." if len(s) > max_len else s


def extract_json(content: str) -> Dict[str, Any]:
    """
    Extract and validate JSON from AI response with better error handling.
    """
    logger.debug(
        f"[JSON-EXTRACT-START] content_len={len(content)} | "
        f"first_char={repr(content[0]) if content else 'empty'} | "
        f"last_char={repr(content[-1]) if content else 'empty'}"
    )

    try:
        # Direct JSON parsing (works with response_mime_type="application/json")
        result = json.loads(content)
        logger.debug("[JSON-EXTRACT] direct parse success")
        return result
    except json.JSONDecodeError as e:
        logger.warning(
            f"[JSON-PARSE-FAIL-DIRECT] error={e.msg} | "
            f"pos={e.pos} | "
            f"line={e.lineno} | "
            f"col={e.colno} | "
            f"context={truncate(content[max(0, e.pos-30):e.pos+30], 60)}"
        )

        # Try to fix common JSON issues
        cleaned_content = clean_json_content(content)
        if cleaned_content:
            logger.debug(
                f"[JSON-CLEAN] original_len={len(content)} | "
                f"cleaned_len={len(cleaned_content)} | "
                f"diff={len(content) - len(cleaned_content)}"
            )
            try:
                result = json.loads(cleaned_content)
                logger.info("[JSON-EXTRACT] cleaned parse success")
                return result
            except json.JSONDecodeError as e2:
                logger.warning(
                    f"[JSON-PARSE-FAIL-CLEANED] error={e2.msg} | "
                    f"pos={e2.pos} | "
                    f"context={truncate(cleaned_content[max(0, e2.pos-30):e2.pos+30], 60)}"
                )

        # Fallback: try to find JSON in markdown code block
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1).strip()
            logger.debug(
                f"[JSON-MARKDOWN] found markdown block | "
                f"extracted_len={len(json_content)}"
            )
            try:
                result = json.loads(json_content)
                logger.info("[JSON-EXTRACT] markdown parse success")
                return result
            except json.JSONDecodeError as e3:
                logger.warning(
                    f"[JSON-PARSE-FAIL-MARKDOWN] error={e3.msg} | pos={e3.pos}"
                )

        # Last resort: find any JSON-like structure
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            json_content = json_match.group(0)
            logger.debug(
                f"[JSON-REGEX] found JSON structure | "
                f"extracted_len={len(json_content)}"
            )
            try:
                cleaned_json = clean_json_content(json_content)
                if cleaned_json:
                    result = json.loads(cleaned_json)
                    logger.info("[JSON-EXTRACT] regex+clean parse success")
                    return result
            except json.JSONDecodeError as e4:
                logger.warning(f"[JSON-PARSE-FAIL-REGEX] error={e4.msg} | pos={e4.pos}")

        # Log the problematic content for debugging (truncated)
        content_preview = content[:500] + "..." if len(content) > 500 else content
        logger.error(
            f"[JSON-EXTRACT-FAILED] all parsing attempts failed | "
            f"content_preview={content_preview}"
        )
        raise ValueError(f"Could not extract valid JSON from response: {str(e)}")


def clean_json_content(content: str) -> str:
    """
    Clean and recover truncated JSON from token limit cutoffs.
    Strategy: Find last complete suggestion object and close structures.
    """
    if not content.strip():
        logger.debug("[JSON-CLEAN] empty content, returning empty")
        return ""

    original_len = len(content)
    content = content.strip()

    # Strategy: Find positions of complete top-level objects in suggestions array
    # Look for pattern: complete {...} objects at depth 2 (inside suggestions array)

    in_string = False
    escape_next = False
    depth = 0  # Brace depth
    bracket_depth = 0  # Bracket depth
    last_complete_suggestion_end = -1
    object_start_depth = -1
    complete_objects_count = 0
    root_object_end = -1  # Position where root JSON object ends

    i = 0
    while i < len(content):
        char = content[i]

        if escape_next:
            escape_next = False
            i += 1
            continue

        if char == "\\" and in_string:
            escape_next = True
            i += 1
            continue

        if char == '"':
            in_string = not in_string
            i += 1
            continue

        if in_string:
            i += 1
            continue

        # Track structure depth
        if char == "{":
            depth += 1
            # Track when we enter a suggestion object (depth 2, inside suggestions array)
            if depth == 2 and bracket_depth == 1:
                object_start_depth = depth
        elif char == "}":
            # Check if we're closing a suggestion object
            if depth == 2 and object_start_depth == 2:
                last_complete_suggestion_end = i + 1
                complete_objects_count += 1
                object_start_depth = -1
            depth = max(0, depth - 1)
            # Track when root object closes (depth returns to 0)
            if depth == 0 and bracket_depth == 0 and root_object_end == -1:
                root_object_end = i + 1
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth = max(0, bracket_depth - 1)
            # Track when root array closes
            if depth == 0 and bracket_depth == 0 and root_object_end == -1:
                root_object_end = i + 1

        i += 1

    # Check if JSON is incomplete (unclosed structures or in string)
    is_incomplete = in_string or depth > 0 or bracket_depth > 0

    logger.debug(
        f"[JSON-CLEAN-ANALYSIS] original_len={original_len} | "
        f"in_string={in_string} | "
        f"unclosed_braces={depth} | "
        f"unclosed_brackets={bracket_depth} | "
        f"complete_objects={complete_objects_count} | "
        f"last_complete_pos={last_complete_suggestion_end} | "
        f"root_object_end={root_object_end} | "
        f"is_incomplete={is_incomplete}"
    )

    # If there's extra text after a complete JSON object, truncate it
    if not is_incomplete and root_object_end > 0 and root_object_end < len(content):
        extra_text = content[root_object_end:].strip()
        if extra_text:
            logger.debug(
                f"[JSON-CLEAN-EXTRA-TEXT] removing {len(content) - root_object_end} chars "
                f"after complete JSON at pos {root_object_end}"
            )
            content = content[:root_object_end]

    # Always fix trailing commas before closing braces/brackets (common AI output issue)
    original_content = content
    content = re.sub(r",(\s*[}\]])", r"\1", content)
    if content != original_content:
        logger.debug(
            "[JSON-CLEAN-TRAILING-COMMA] removed trailing comma before closing brace/bracket"
        )

    # Fix missing commas between array elements or object properties (common AI output issue)
    original_content = content

    # Pattern: } followed by whitespace (including newline) then { (missing comma between objects)
    content = re.sub(r"\}(\s*\n\s*)\{", r"},\1{", content)

    # Pattern: ] followed by whitespace (including newline) then [ (missing comma between arrays)
    content = re.sub(r"\](\s*\n\s*)\[", r"],\1[", content)

    # Pattern: } followed by whitespace (including newline) then " (object end, then property key)
    content = re.sub(r'\}(\s*\n\s*)"', r'},\1"', content)

    # Pattern: ] followed by whitespace (including newline) then " (array end, then property key)
    content = re.sub(r'\](\s*\n\s*)"', r'],\1"', content)

    # Also handle single-line JSON with spaces (but be conservative - require at least 2 spaces)
    content = re.sub(r"\}(  +)\{", r"},\1{", content)
    content = re.sub(r"\](  +)\[", r"],\1[", content)

    if content != original_content:
        logger.debug(
            "[JSON-CLEAN-MISSING-COMMA] added missing commas between JSON structures"
        )

    if is_incomplete and last_complete_suggestion_end > 0:
        # Truncate to last complete suggestion
        truncated_len = len(content) - last_complete_suggestion_end
        content = content[:last_complete_suggestion_end]
        # Close the suggestions array and root object
        content += "]}"
        logger.info(
            f"[JSON-CLEAN-RECOVERY] truncated {truncated_len} chars | "
            f"kept {last_complete_suggestion_end} chars | "
            f"preserved {complete_objects_count} complete objects | "
            f"added closing ']}}'"
        )
    elif is_incomplete:
        # No complete suggestions found, try simpler recovery
        logger.warning(
            "[JSON-CLEAN-FALLBACK] no complete objects found | "
            "attempting simple recovery"
        )
        # Find last complete key-value pair
        last_valid = find_last_valid_json_position(content)
        if last_valid > 0:
            content = content[:last_valid]
            logger.debug(f"[JSON-CLEAN-TRUNCATE] cut at last_valid={last_valid}")

        # Remove trailing incomplete content
        content = re.sub(r",\s*$", "", content)
        content = re.sub(r":\s*$", ": null", content)  # Fix hanging colons
        content = re.sub(r",(\s*[}\]])", r"\1", content)

        # Close structures
        content = close_json_structures(content)
        logger.debug(f"[JSON-CLEAN-CLOSED] final_len={len(content)}")

    return content


def find_last_valid_json_position(content: str) -> int:
    """Find position after last complete JSON value."""
    in_string = False
    escape_next = False
    last_valid = 0

    for i, char in enumerate(content):
        if escape_next:
            escape_next = False
            continue
        if char == "\\" and in_string:
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            if not in_string:  # Just closed a string
                last_valid = i + 1
            continue
        if in_string:
            continue
        if char in "}]":
            last_valid = i + 1
        elif char == ",":
            last_valid = i

    return last_valid


def close_json_structures(content: str) -> str:
    """Close any unclosed JSON structures."""
    in_string = False
    escape_next = False
    structure_stack = []

    for char in content:
        if escape_next:
            escape_next = False
            continue
        if char == "\\" and in_string:
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char in "{[":
            structure_stack.append(char)
        elif char == "}" and structure_stack and structure_stack[-1] == "{":
            structure_stack.pop()
        elif char == "]" and structure_stack and structure_stack[-1] == "[":
            structure_stack.pop()

    # Close in reverse order
    for opener in reversed(structure_stack):
        content += "]" if opener == "[" else "}"

    return content

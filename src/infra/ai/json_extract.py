"""
Unified JSON extraction for AI responses.

Combines:
- Truncation detection (raises with a user-friendly message)
- Full JSON repair: trailing-comma removal, missing-comma insertion, structure closing
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def extract_json(content: str) -> dict[str, Any]:
    """
    Extract and validate JSON from an AI response string.

    Attempts in order:
    1. Direct json.loads
    2. Clean and repair common AI output issues, then json.loads
    3. Extract from markdown code block (```json ... ```)
    4. Extract any JSON-like structure with regex, then repair

    Raises:
        ValueError: If the response is truncated or no valid JSON can be extracted.
    """
    logger.debug(
        "[JSON-EXTRACT-START] content_len=%d first=%r last=%r",
        len(content),
        content[0] if content else "",
        content[-1] if content else "",
    )

    try:
        result = json.loads(content)
        logger.debug("[JSON-EXTRACT] direct parse success")
        return result
    except json.JSONDecodeError as first_err:
        logger.debug(
            "[JSON-PARSE-FAIL-DIRECT] error=%s pos=%s", first_err.msg, first_err.pos
        )

    # Attempt 2: clean + repair
    cleaned = _clean_json(content)
    if cleaned:
        try:
            result = json.loads(cleaned)
            logger.debug("[JSON-EXTRACT] cleaned parse success")
            return result
        except json.JSONDecodeError as e2:
            logger.debug("[JSON-PARSE-FAIL-CLEANED] error=%s pos=%s", e2.msg, e2.pos)

    # Attempt 3: markdown code block
    md_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if md_match:
        try:
            result = json.loads(md_match.group(1).strip())
            logger.debug("[JSON-EXTRACT] markdown parse success")
            return result
        except json.JSONDecodeError as e3:
            logger.debug("[JSON-PARSE-FAIL-MARKDOWN] error=%s pos=%s", e3.msg, e3.pos)

    # Attempt 4: regex grab any {...} structure
    obj_match = re.search(r"\{.*\}", content, re.DOTALL)
    if obj_match:
        try:
            candidate = _clean_json(obj_match.group(0))
            if candidate:
                result = json.loads(candidate)
                logger.debug("[JSON-EXTRACT] regex+clean parse success")
                return result
        except json.JSONDecodeError as e4:
            logger.debug("[JSON-PARSE-FAIL-REGEX] error=%s pos=%s", e4.msg, e4.pos)

    # Truncation detection — raise with user-friendly message
    open_braces = content.count("{")
    close_braces = content.count("}")
    is_truncated = (
        (open_braces > 0 and close_braces == 0)
        or (open_braces > close_braces)
        or content.rstrip().endswith(('":',  '": "', '"name": "', '",'))
    )
    if is_truncated:
        logger.error(
            "[JSON-TRUNCATED] content_len=%d open_braces=%d close_braces=%d",
            len(content),
            open_braces,
            close_braces,
        )
        raise ValueError(
            "AI response was truncated. Please try again with a simpler image."
        )

    logger.error(
        "[JSON-EXTRACT-FAILED] all attempts failed content_len=%d", len(content)
    )
    from src.observability import increment_metric  # noqa: PLC0415
    increment_metric(
        "ai.vision.parse_failure.count",
        attributes={"content_len_bucket": _content_len_bucket(len(content))},
    )
    raise ValueError(
        "Could not extract valid JSON from AI response. "
        "Please try again or use a clearer image."
    )


# ---------------------------------------------------------------------------
# Internal helpers (not part of public API)
# ---------------------------------------------------------------------------


def _content_len_bucket(n: int) -> str:
    """Map content byte length to a low-cardinality bucket label for metrics."""
    if n < 100:
        return "0-100"
    if n < 500:
        return "100-500"
    if n < 2000:
        return "500-2000"
    return "2000+"


def _clean_json(content: str) -> str:
    """
    Repair common AI output issues in a JSON string.

    - Removes trailing commas before ] or }
    - Adds missing commas between objects/arrays
    - Recovers truncated structures by truncating to last complete object
    - Closes unclosed braces/brackets
    """
    if not content.strip():
        return ""

    original_len = len(content)
    content = content.strip()

    # Structural analysis
    in_string = False
    escape_next = False
    depth = 0
    bracket_depth = 0
    last_complete_obj_end = -1
    object_start_depth = -1
    complete_objects_count = 0
    root_end = -1

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

        if char == "{":
            depth += 1
            if depth == 2 and bracket_depth == 1:
                object_start_depth = depth
        elif char == "}":
            if depth == 2 and object_start_depth == 2:
                last_complete_obj_end = i + 1
                complete_objects_count += 1
                object_start_depth = -1
            depth = max(0, depth - 1)
            if depth == 0 and bracket_depth == 0 and root_end == -1:
                root_end = i + 1
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth = max(0, bracket_depth - 1)
            if depth == 0 and bracket_depth == 0 and root_end == -1:
                root_end = i + 1

        i += 1

    is_incomplete = in_string or depth > 0 or bracket_depth > 0

    logger.debug(
        "[JSON-CLEAN] original_len=%d in_string=%s unclosed_braces=%d "
        "unclosed_brackets=%d complete_objects=%d root_end=%d is_incomplete=%s",
        original_len,
        in_string,
        depth,
        bracket_depth,
        complete_objects_count,
        root_end,
        is_incomplete,
    )

    # Trim trailing text after a complete root object
    if not is_incomplete and root_end > 0 and root_end < len(content):
        extra = content[root_end:].strip()
        if extra:
            logger.debug(
                "[JSON-CLEAN-EXTRA-TEXT] removing %d chars after pos %d",
                len(content) - root_end,
                root_end,
            )
            content = content[:root_end]

    # Fix trailing commas before closing delimiters
    prev = content
    content = re.sub(r",(\s*[}\]])", r"\1", content)
    if content != prev:
        logger.debug("[JSON-CLEAN-TRAILING-COMMA] removed trailing commas")

    # Fix missing commas between adjacent objects/arrays
    prev = content
    content = re.sub(r"\}(\s*\n\s*)\{", r"},\1{", content)
    content = re.sub(r"\](\s*\n\s*)\[", r"],\1[", content)
    content = re.sub(r'\}(\s*\n\s*)"', r'},\1"', content)
    content = re.sub(r'\](\s*\n\s*)"', r'],\1"', content)
    content = re.sub(r"\}(  +)\{", r"},\1{", content)
    content = re.sub(r"\](  +)\[", r"],\1[", content)
    if content != prev:
        logger.debug("[JSON-CLEAN-MISSING-COMMA] inserted missing commas")

    if is_incomplete and last_complete_obj_end > 0:
        truncated_len = len(content) - last_complete_obj_end
        content = content[:last_complete_obj_end] + "]}"
        logger.debug(
            "[JSON-CLEAN-RECOVERY] truncated %d chars, preserved %d complete objects",
            truncated_len,
            complete_objects_count,
        )
    elif is_incomplete:
        logger.warning("[JSON-CLEAN-FALLBACK] no complete objects, attempting close")
        candidate = re.sub(r",\s*$", "", content)
        candidate = re.sub(r":\s*$", ": null", candidate)
        candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
        candidate = _close_structures(candidate)
        try:
            json.loads(candidate)
            content = candidate
            logger.debug("[JSON-CLEAN-CLOSED] final_len=%d", len(content))
        except json.JSONDecodeError as e:
            logger.debug("[JSON-CLEAN-CLOSE-FAILED] error=%s pos=%s", e.msg, e.pos)
            last_valid = _find_last_valid_position(content)
            if last_valid > 0:
                content = content[:last_valid]
            content = re.sub(r",\s*$", "", content)
            content = re.sub(r":\s*$", ": null", content)
            content = re.sub(r",(\s*[}\]])", r"\1", content)
            content = _close_structures(content)
            logger.debug("[JSON-CLEAN-CLOSED] final_len=%d", len(content))

    return content


def _find_last_valid_position(content: str) -> int:
    """Return the index after the last complete JSON value."""
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
            if not in_string:
                last_valid = i + 1
            continue
        if in_string:
            continue
        if char in "}]":
            last_valid = i + 1
        elif char == ",":
            last_valid = i

    return last_valid


def _close_structures(content: str) -> str:
    """Close any unclosed braces/brackets in a JSON string."""
    in_string = False
    escape_next = False
    stack: list[str] = []

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
            stack.append(char)
        elif char == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif char == "]" and stack and stack[-1] == "[":
            stack.pop()

    if in_string:
        content += '"'
    for opener in reversed(stack):
        content += "]" if opener == "[" else "}"

    return content

"""
Meal generation service implementation using Google Gemini API.
Follows clean architecture pattern with single LLM handling different prompts.
"""
import json
import logging
import os
import re
import time
from typing import Dict, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.domain.ports.meal_generation_service_port import MealGenerationServicePort

logger = logging.getLogger(__name__)


def _truncate(s: str, max_len: int = 200) -> str:
    """Truncate string for logging."""
    return s[:max_len] + "..." if len(s) > max_len else s


class MealGenerationService(MealGenerationServicePort):
    """
    Unified meal generation service using single LLM with different prompts.
    Follows clean architecture principles.
    """
    
    def __init__(self):
        """Initialize the single Gemini LLM client."""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not found. AI meal generation will not be available.")
            self.llm = None
        else:
            # Base LLM configuration - will be customized per request
            self.base_llm_config = {
                "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                "temperature": 0.2,  # Lower temperature for consistency
                "google_api_key": self.api_key,
                # NOTE: response_mime_type is set conditionally per request
                # (incompatible with structured output / function calling)
            }
    
    def generate_meal_plan(
        self, 
        prompt: str, 
        system_message: str, 
        response_type: str = "json", 
        max_tokens: int = None,
        schema: type = None
    ) -> Dict[str, Any]:
        """
        Generate meal plan using provided prompt and system message.
        Single entry point for all meal generation.

        Args:
            prompt: The generation prompt
            system_message: System instructions
            response_type: Response format ("json" or "text")
            max_tokens: Optional max tokens override (defaults based on complexity)
            schema: Optional Pydantic model for structured output (recommended for reliability)
        
        Returns:
            Dict or Pydantic model instance (if schema provided)
        """
        if not self.api_key:
            raise RuntimeError("GOOGLE_API_KEY missing — cannot call Gemini.")

        start_time = time.time()

        try:
            # Determine optimal token limit based on content complexity
            if max_tokens is None:
                max_tokens = self._determine_optimal_tokens(prompt, system_message)

            # Log request config
            model_name = self.base_llm_config.get("model", "unknown")
            logger.info(
                f"[AI-REQUEST] model={model_name} | "
                f"max_tokens={max_tokens} | "
                f"prompt_len={len(prompt)} | "
                f"system_len={len(system_message)} | "
                f"response_type={response_type}"
            )

            # Create LLM instance with appropriate token limit
            # Add response_mime_type only if NOT using structured output (incompatible)
            llm_config = {
                **self.base_llm_config,
                "max_output_tokens": max_tokens,
            }
            
            # Only set response_mime_type for legacy JSON mode (not structured output)
            if not schema and response_type == "json":
                llm_config["response_mime_type"] = "application/json"
            
            llm = ChatGoogleGenerativeAI(**llm_config)

            # Use structured output if schema provided (guarantees valid format)
            if schema:
                logger.info(f"[STRUCTURED-OUTPUT] using schema={schema.__name__}")
                # NOTE: with_structured_output uses function calling, incompatible with response_mime_type
                # Use include_raw=True to get raw response as fallback when parsing fails
                llm_with_structure = llm.with_structured_output(schema, include_raw=True)
                
                # Create messages
                messages = [
                    SystemMessage(content=system_message),
                    HumanMessage(content=prompt)
                ]
                
                # Generate structured response (returns dict with 'raw' and 'parsed')
                result = llm_with_structure.invoke(messages)
                elapsed = time.time() - start_time
                
                # Extract parsed response (or None if parsing failed)
                structured_response = result.get("parsed") if isinstance(result, dict) else result
                raw_response = result.get("raw") if isinstance(result, dict) else None
                
                logger.info(
                    f"[STRUCTURED-RESPONSE] elapsed={elapsed:.2f}s | "
                    f"schema={schema.__name__} | "
                    f"parsed_type={type(structured_response).__name__} | "
                    f"has_raw={raw_response is not None}"
                )
                
                # Handle None response - try to use raw response as fallback
                if structured_response is None:
                    if raw_response and hasattr(raw_response, 'content'):
                        raw_content = raw_response.content
                        logger.warning(
                            f"[STRUCTURED-OUTPUT-FALLBACK] schema={schema.__name__} | "
                            f"Attempting legacy JSON parse on raw content | "
                            f"raw_len={len(raw_content) if raw_content else 0}"
                        )
                        # Try legacy JSON parsing as fallback
                        try:
                            fallback_data = self._extract_json(raw_content)
                            logger.info(f"[STRUCTURED-OUTPUT-FALLBACK-SUCCESS] Parsed raw JSON successfully")
                            return fallback_data
                        except Exception as json_err:
                            logger.error(
                                f"[STRUCTURED-OUTPUT-FALLBACK-FAILED] "
                                f"JSON parse also failed: {json_err}"
                            )
                    
                    logger.error(
                        f"[STRUCTURED-OUTPUT-NONE] schema={schema.__name__} | "
                        f"elapsed={elapsed:.2f}s | "
                        f"Model failed to generate valid structured data"
                    )
                    raise ValueError(
                        f"Structured output returned None for schema {schema.__name__}. "
                        f"Model failed to generate data matching the required format."
                    )
                
                # Convert to dict for consistent interface
                if hasattr(structured_response, 'model_dump'):
                    return structured_response.model_dump()
                elif hasattr(structured_response, 'dict'):
                    return structured_response.dict()
                else:
                    return dict(structured_response)
            
            # Legacy JSON parsing (when no schema provided)
            # Create messages
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=prompt)
            ]

            # Generate response
            response = llm.invoke(messages)
            content = response.content
            elapsed = time.time() - start_time

            # Log response details
            logger.info(
                f"[AI-RESPONSE] elapsed={elapsed:.2f}s | "
                f"content_len={len(content)} chars (~{len(content)//4} tokens) | "
                f"starts_with={_truncate(content[:50], 50)} | "
                f"ends_with={_truncate(content[-50:] if len(content) > 50 else content, 50)}"
            )

            # Extract and validate JSON
            if response_type == "json":
                data = self._extract_json(content)
                logger.debug(
                    f"[AI-PARSED] keys={list(data.keys()) if isinstance(data, dict) else 'non-dict'}"
                )
                return data
            else:
                return {"raw_content": content}

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"[AI-ERROR] elapsed={elapsed:.2f}s | "
                f"error_type={type(e).__name__} | "
                f"error={str(e)[:200]}"
            )
            raise
    
    def _determine_optimal_tokens(self, prompt: str, system_message: str) -> int:
        """
        Determine optimal token limit based on content complexity.

        Returns:
            Appropriate max_output_tokens value
        """
        # Analyze prompt content to estimate complexity
        content_indicators = {
            # Weekly plans need more tokens
            'weekly': ['week', '7 days', 'monday', 'tuesday', 'wednesday'],
            # Multiple suggestions with full details (ingredients, recipe steps)
            'suggestions': ['suggestions', 'meal ideas', 'recipe_steps', 'ingredients (array'],
            # Multiple meals need moderate tokens
            'daily_multiple': ['breakfast', 'lunch', 'dinner', 'snack'],
            # Single meals need fewer tokens
            'single': ['single meal', 'one meal', 'generate a meal']
        }

        combined_text = (prompt + " " + system_message).lower()

        # Check for weekly plan indicators
        if any(indicator in combined_text for indicator in content_indicators['weekly']):
            logger.debug("Detected weekly plan generation - using high token limit")
            return 8000  # Increased back to 8000 for complete weekly plans

        # Check for multiple suggestions with full recipe details
        if any(indicator in combined_text for indicator in content_indicators['suggestions']):
            # Extract number of suggestions requested - handle formats like:
            # "3 meal suggestions", "exactly 3 different breakfast meal suggestions"
            suggestion_count_match = re.search(
                r'(?:exactly\s+)?(\d+)\s+(?:\w+\s+)*(?:meal\s+)?suggestions?',
                combined_text
            )
            if suggestion_count_match:
                count = int(suggestion_count_match.group(1))
                # Each full suggestion with ingredients + instructions + seasonings ~1500 tokens
                tokens = max(4000, count * 1500)
                logger.debug(f"Detected {count} meal suggestions - using {tokens} token limit")
                return min(tokens, 8000)  # Cap at 8000
            logger.debug("Detected meal suggestions generation - using medium-high token limit")
            return 5000  # Default for suggestions with full details (increased from 3500)

        # Check for daily multiple meals
        meal_types_found = sum(1 for indicator in content_indicators['daily_multiple']
                              if indicator in combined_text)
        if meal_types_found >= 3:
            logger.debug("Detected daily multiple meal generation - using medium token limit")
            return 3000  # Medium for daily plans with multiple meals

        # Single meal or simple requests
        logger.debug("Detected simple meal generation - using low token limit")
        return 1500  # Conservative for single meals
    
    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract and validate JSON from AI response with better error handling."""
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
                f"context={_truncate(content[max(0, e.pos-30):e.pos+30], 60)}"
            )

            # Try to fix common JSON issues
            cleaned_content = self._clean_json_content(content)
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
                        f"context={_truncate(cleaned_content[max(0, e2.pos-30):e2.pos+30], 60)}"
                    )

            # Fallback: try to find JSON in markdown code block
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
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
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_content = json_match.group(0)
                logger.debug(
                    f"[JSON-REGEX] found JSON structure | "
                    f"extracted_len={len(json_content)}"
                )
                try:
                    cleaned_json = self._clean_json_content(json_content)
                    if cleaned_json:
                        result = json.loads(cleaned_json)
                        logger.info("[JSON-EXTRACT] regex+clean parse success")
                        return result
                except json.JSONDecodeError as e4:
                    logger.warning(
                        f"[JSON-PARSE-FAIL-REGEX] error={e4.msg} | pos={e4.pos}"
                    )

            # Log the problematic content for debugging (truncated)
            content_preview = content[:500] + "..." if len(content) > 500 else content
            logger.error(
                f"[JSON-EXTRACT-FAILED] all parsing attempts failed | "
                f"content_preview={content_preview}"
            )
            raise ValueError(f"Could not extract valid JSON from response: {str(e)}")
    
    def _clean_json_content(self, content: str) -> str:
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

            if char == '\\' and in_string:
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
            if char == '{':
                depth += 1
                # Track when we enter a suggestion object (depth 2, inside suggestions array)
                if depth == 2 and bracket_depth == 1:
                    object_start_depth = depth
            elif char == '}':
                # Check if we're closing a suggestion object
                if depth == 2 and object_start_depth == 2:
                    last_complete_suggestion_end = i + 1
                    complete_objects_count += 1
                    object_start_depth = -1
                depth = max(0, depth - 1)
                # Track when root object closes (depth returns to 0)
                if depth == 0 and bracket_depth == 0 and root_object_end == -1:
                    root_object_end = i + 1
            elif char == '[':
                bracket_depth += 1
            elif char == ']':
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
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        if content != original_content:
            logger.debug("[JSON-CLEAN-TRAILING-COMMA] removed trailing comma before closing brace/bracket")

        # Fix missing commas between array elements or object properties (common AI output issue)
        # These patterns use }\s+{ or ]\s+" to ensure there's whitespace (newlines) between
        # which indicates structure boundaries, not content inside strings
        original_content = content

        # Pattern: } followed by whitespace (including newline) then { (missing comma between objects)
        content = re.sub(r'\}(\s*\n\s*)\{', r'},\1{', content)

        # Pattern: ] followed by whitespace (including newline) then [ (missing comma between arrays)
        content = re.sub(r'\](\s*\n\s*)\[', r'],\1[', content)

        # Pattern: } followed by whitespace (including newline) then " (object end, then property key)
        content = re.sub(r'\}(\s*\n\s*)"', r'},\1"', content)

        # Pattern: ] followed by whitespace (including newline) then " (array end, then property key)
        content = re.sub(r'\](\s*\n\s*)"', r'],\1"', content)

        # Also handle single-line JSON with spaces (but be conservative - require at least 2 spaces)
        content = re.sub(r'\}(  +)\{', r'},\1{', content)
        content = re.sub(r'\](  +)\[', r'],\1[', content)

        if content != original_content:
            logger.debug("[JSON-CLEAN-MISSING-COMMA] added missing commas between JSON structures")

        if is_incomplete and last_complete_suggestion_end > 0:
            # Truncate to last complete suggestion
            truncated_len = len(content) - last_complete_suggestion_end
            content = content[:last_complete_suggestion_end]
            # Close the suggestions array and root object
            content += ']}'
            logger.info(
                f"[JSON-CLEAN-RECOVERY] truncated {truncated_len} chars | "
                f"kept {last_complete_suggestion_end} chars | "
                f"preserved {complete_objects_count} complete objects | "
                f"added closing ']}}'"
            )
        elif is_incomplete:
            # No complete suggestions found, try simpler recovery
            logger.warning(
                f"[JSON-CLEAN-FALLBACK] no complete objects found | "
                f"attempting simple recovery"
            )
            # Find last complete key-value pair
            last_valid = self._find_last_valid_json_position(content)
            if last_valid > 0:
                content = content[:last_valid]
                logger.debug(
                    f"[JSON-CLEAN-TRUNCATE] cut at last_valid={last_valid}"
                )

            # Remove trailing incomplete content
            content = re.sub(r',\s*$', '', content)
            content = re.sub(r':\s*$', ': null', content)  # Fix hanging colons
            content = re.sub(r',(\s*[}\]])', r'\1', content)

            # Close structures
            content = self._close_json_structures(content)
            logger.debug(
                f"[JSON-CLEAN-CLOSED] final_len={len(content)}"
            )

        return content

    def _find_last_valid_json_position(self, content: str) -> int:
        """Find position after last complete JSON value."""
        in_string = False
        escape_next = False
        last_valid = 0

        for i, char in enumerate(content):
            if escape_next:
                escape_next = False
                continue
            if char == '\\' and in_string:
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                if not in_string:  # Just closed a string
                    last_valid = i + 1
                continue
            if in_string:
                continue
            if char in '}]':
                last_valid = i + 1
            elif char == ',':
                last_valid = i

        return last_valid

    def _close_json_structures(self, content: str) -> str:
        """Close any unclosed JSON structures."""
        in_string = False
        escape_next = False
        structure_stack = []

        for char in content:
            if escape_next:
                escape_next = False
                continue
            if char == '\\' and in_string:
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char in '{[':
                structure_stack.append(char)
            elif char == '}' and structure_stack and structure_stack[-1] == '{':
                structure_stack.pop()
            elif char == ']' and structure_stack and structure_stack[-1] == '[':
                structure_stack.pop()

        # Close in reverse order
        for opener in reversed(structure_stack):
            content += ']' if opener == '[' else '}'

        return content
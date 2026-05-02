"""
Meal generation service implementation using Google Gemini API.
Follows clean architecture pattern with single LLM handling different prompts.
"""

import logging
import os
import re
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.infra.adapters.meal_generation_json_utils import (
    extract_json,
    truncate,
)
from src.infra.services.ai.gemini_model_manager import (
    GeminiModelManager,
    GeminiModelPurpose,
)
from src.api.exceptions import ExternalServiceException
from src.infra.services.ai.gemini_error_utils import is_rate_limit_error

try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:
    ResourceExhausted = None

logger = logging.getLogger(__name__)


class MealGenerationService(MealGenerationServicePort):
    """
    Unified meal generation service using single LLM with different prompts.
    Follows clean architecture principles.
    """

    def __init__(self):
        """Initialize the service with singleton model manager."""
        try:
            self._model_manager = GeminiModelManager.get_instance()
        except ValueError:
            logger.warning(
                "GOOGLE_API_KEY not found. AI meal generation will not be available."
            )
            self._model_manager = None

    def generate_meal_plan(
        self,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: int = None,
        schema: type = None,
        model_purpose: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate meal plan using provided prompt and system message.
        Single entry point for all meal generation.

        Args:
            prompt: The generation prompt
            system_message: System instructions
            response_type: Response format ("json" or "text")
            max_tokens: Optional max tokens override (defaults based on complexity)
            schema: Optional Pydantic model for structured output (recommended for reliability)
            model_purpose: Optional purpose for rate limit distribution
                          ("meal_names", "recipe_primary", "recipe_secondary")

        Returns:
            Dict or Pydantic model instance (if schema provided)
        """
        if not self._model_manager:
            raise RuntimeError("GOOGLE_API_KEY missing — cannot call Gemini.")

        start_time = time.time()

        # Resolve model purpose for rate limit distribution
        purpose = GeminiModelPurpose.GENERAL
        if model_purpose:
            try:
                purpose = GeminiModelPurpose(model_purpose)
            except ValueError:
                logger.warning(f"Unknown model_purpose: {model_purpose}, using GENERAL")

        try:
            # Determine optimal token limit based on content complexity
            if max_tokens is None:
                max_tokens = self._determine_optimal_tokens(prompt, system_message)

            # Get model name for logging (mirrors GeminiModelManager.get_model_for_purpose logic)
            from src.infra.services.ai.gemini_model_config import (
                PURPOSE_ENV_VARS,
                PURPOSE_MODEL_DEFAULTS,
            )

            env_var = PURPOSE_ENV_VARS.get(purpose, "GEMINI_MODEL")
            model_name = os.getenv(
                env_var,
                PURPOSE_MODEL_DEFAULTS.get(purpose, self._model_manager.model_name),
            )

            # Log request config with purpose
            logger.debug(
                f"[AI-REQUEST] purpose={purpose.value} | model={model_name} | "
                f"max_tokens={max_tokens} | "
                f"prompt_len={len(prompt)} | "
                f"system_len={len(system_message)} | "
                f"response_type={response_type}"
            )

            # Get LLM instance from singleton manager using purpose-based selection
            # Only set response_mime_type for legacy JSON mode (not structured output)
            response_mime_type = None
            if not schema and response_type == "json":
                response_mime_type = "application/json"

            # Use purpose-aware model getter for rate limit distribution
            llm = self._model_manager.get_model_for_purpose(
                purpose=purpose,
                max_output_tokens=max_tokens,
                response_mime_type=response_mime_type,
            )

            # Use structured output if schema provided (guarantees valid format)
            if schema:
                logger.debug(f"[STRUCTURED-OUTPUT] using schema={schema.__name__}")
                # NOTE: with_structured_output uses function calling, incompatible with response_mime_type
                # Use include_raw=True to get raw response as fallback when parsing fails
                llm_with_structure = llm.with_structured_output(
                    schema, include_raw=True
                )

                # Create messages
                messages = [
                    SystemMessage(content=system_message),
                    HumanMessage(content=prompt),
                ]

                # Generate structured response (returns dict with 'raw' and 'parsed')
                result = llm_with_structure.invoke(messages)
                elapsed = time.time() - start_time

                # Extract parsed response (or None if parsing failed)
                structured_response = (
                    result.get("parsed") if isinstance(result, dict) else result
                )
                raw_response = result.get("raw") if isinstance(result, dict) else None

                logger.debug(
                    f"[STRUCTURED-RESPONSE] elapsed={elapsed:.2f}s | "
                    f"schema={schema.__name__} | "
                    f"parsed_type={type(structured_response).__name__} | "
                    f"has_raw={raw_response is not None}"
                )

                # Handle None response - try to use raw response as fallback
                if structured_response is None:
                    if raw_response and hasattr(raw_response, "content"):
                        raw_content = raw_response.content
                        logger.warning(
                            f"[STRUCTURED-OUTPUT-FALLBACK] schema={schema.__name__} | "
                            f"Attempting legacy JSON parse on raw content | "
                            f"raw_len={len(raw_content) if raw_content else 0}"
                        )
                        # Try legacy JSON parsing as fallback
                        try:
                            fallback_data = extract_json(raw_content)
                            logger.debug(
                                "[STRUCTURED-OUTPUT-FALLBACK-SUCCESS] Parsed raw JSON successfully"
                            )
                            return fallback_data
                        except Exception as json_err:
                            logger.error(
                                f"[STRUCTURED-OUTPUT-FALLBACK-FAILED] "
                                f"JSON parse also failed: {json_err}"
                            )

                    # E2 FIX: Ultimate fallback to legacy JSON mode
                    logger.warning(
                        f"[E2-LEGACY-FALLBACK] schema={schema.__name__} | "
                        f"Structured output completely failed, retrying with legacy JSON mode"
                    )

                    try:
                        # Get legacy LLM with JSON mode from singleton manager
                        legacy_llm = self._model_manager.get_model(
                            max_output_tokens=max_tokens,
                            response_mime_type="application/json",
                        )

                        # Retry with same prompt but legacy mode
                        legacy_response = legacy_llm.invoke(messages)
                        legacy_elapsed = time.time() - start_time

                        logger.debug(
                            f"[E2-LEGACY-RESPONSE] elapsed={legacy_elapsed:.2f}s | "
                            f"content_len={len(legacy_response.content)}"
                        )

                        # Parse legacy JSON response
                        legacy_data = extract_json(legacy_response.content)
                        logger.debug(
                            "[E2-LEGACY-SUCCESS] Successfully parsed legacy JSON response"
                        )
                        return legacy_data

                    except Exception as legacy_err:
                        logger.error(
                            f"[E2-LEGACY-FAILED] Legacy fallback also failed: {legacy_err}"
                        )
                        raise ValueError(
                            f"Both structured output and legacy JSON mode failed for schema {schema.__name__}. "
                            f"Structured: None response. Legacy: {str(legacy_err)[:100]}"
                        ) from legacy_err

                # Convert to dict for consistent interface
                if hasattr(structured_response, "model_dump"):
                    return structured_response.model_dump()
                elif hasattr(structured_response, "dict"):
                    return structured_response.dict()
                else:
                    return dict(structured_response)

            # Legacy JSON parsing (when no schema provided)
            # Create messages
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=prompt),
            ]

            # Generate response with retry on rate limit errors
            max_attempts = 2
            for attempt in range(max_attempts):
                try:
                    response = llm.invoke(messages)
                    break
                except Exception as invoke_err:
                    if is_rate_limit_error(invoke_err):
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"[AI-RATE-LIMIT] attempt={attempt + 1} | "
                                f"Sleeping 1s before retry | "
                                f"error={str(invoke_err)[:100]}"
                            )
                            time.sleep(1)
                        else:
                            raise ExternalServiceException(
                                message="Gemini API rate limit exceeded after retry",
                                error_code="AI_RATE_LIMITED",
                                details={"retry_after_seconds": 5},
                            )
                    else:
                        raise

            content = response.content
            elapsed = time.time() - start_time

            # Log response details
            logger.debug(
                f"[AI-RESPONSE] elapsed={elapsed:.2f}s | "
                f"content_len={len(content)} chars (~{len(content)//4} tokens) | "
                f"starts_with={truncate(content[:50], 50)} | "
                f"ends_with={truncate(content[-50:] if len(content) > 50 else content, 50)}"
            )

            # Extract and validate JSON
            if response_type == "json":
                data = extract_json(content)
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
            "weekly": ["week", "7 days", "monday", "tuesday", "wednesday"],
            # Multiple suggestions with full details (ingredients, recipe steps)
            "suggestions": [
                "suggestions",
                "meal ideas",
                "recipe_steps",
                "ingredients (array",
            ],
            # Multiple meals need moderate tokens
            "daily_multiple": ["breakfast", "lunch", "dinner", "snack"],
            # Single meals need fewer tokens
            "single": ["single meal", "one meal", "generate a meal"],
        }

        combined_text = (prompt + " " + system_message).lower()

        # Check for weekly plan indicators
        if any(
            indicator in combined_text for indicator in content_indicators["weekly"]
        ):
            logger.debug("Detected weekly plan generation - using high token limit")
            return 8000  # Increased back to 8000 for complete weekly plans

        # Check for multiple suggestions with full recipe details
        if any(
            indicator in combined_text
            for indicator in content_indicators["suggestions"]
        ):
            # Extract number of suggestions requested - handle formats like:
            # "3 meal suggestions", "exactly 3 different breakfast meal suggestions"
            suggestion_count_match = re.search(
                r"(?:exactly\s+)?(\d+)\s+(?:\w+\s+)*(?:meal\s+)?suggestions?",
                combined_text,
            )
            if suggestion_count_match:
                count = int(suggestion_count_match.group(1))
                # Each full suggestion with ingredients + instructions + seasonings ~1500 tokens
                tokens = max(4000, count * 1500)
                logger.debug(
                    f"Detected {count} meal suggestions - using {tokens} token limit"
                )
                return min(tokens, 8000)  # Cap at 8000
            logger.debug(
                "Detected meal suggestions generation - using medium-high token limit"
            )
            return (
                5000  # Default for suggestions with full details (increased from 3500)
            )

        # Check for daily multiple meals
        meal_types_found = sum(
            1
            for indicator in content_indicators["daily_multiple"]
            if indicator in combined_text
        )
        if meal_types_found >= 3:
            logger.debug(
                "Detected daily multiple meal generation - using medium token limit"
            )
            return 3000  # Medium for daily plans with multiple meals

        # Single meal or simple requests
        logger.debug("Detected simple meal generation - using low token limit")
        return 1500  # Conservative for single meals

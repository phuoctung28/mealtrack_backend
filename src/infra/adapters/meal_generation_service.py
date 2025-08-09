"""
Meal generation service implementation using Google Gemini API.
Follows clean architecture pattern with single LLM handling different prompts.
"""
import json
import logging
import os
import re
from typing import Dict, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.domain.ports.meal_generation_service_port import MealGenerationServicePort

logger = logging.getLogger(__name__)


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
                "model": "gemini-1.5-flash",
                "temperature": 0.2,  # Lower temperature for consistency
                "google_api_key": self.api_key,
                "response_mime_type": "application/json",  # Always expect JSON
            }
    
    def generate_meal_plan(self, prompt: str, system_message: str, response_type: str = "json", max_tokens: int = None) -> Dict[str, Any]:
        """
        Generate meal plan using provided prompt and system message.
        Single entry point for all meal generation.
        
        Args:
            prompt: The generation prompt
            system_message: System instructions
            response_type: Response format ("json" or "text")
            max_tokens: Optional max tokens override (defaults based on complexity)
        """
        if not self.api_key:
            raise RuntimeError("GOOGLE_API_KEY missing — cannot call Gemini.")
        
        try:
            # Determine optimal token limit based on content complexity
            if max_tokens is None:
                max_tokens = self._determine_optimal_tokens(prompt, system_message)
            
            # Create LLM instance with appropriate token limit
            llm = ChatGoogleGenerativeAI(
                **self.base_llm_config,
                max_output_tokens=max_tokens
            )
            
            # Create messages
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=prompt)
            ]
            
            # Generate response
            response = llm.invoke(messages)
            content = response.content
            
            # Extract and validate JSON
            if response_type == "json":
                data = self._extract_json(content)
                return data
            else:
                return {"raw_content": content}
                
        except Exception as e:
            logger.error(f"Error generating meal plan: {str(e)}")
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
            # Multiple meals need moderate tokens  
            'daily_multiple': ['breakfast', 'lunch', 'dinner', 'snack'],
            # Single meals need fewer tokens
            'single': ['single meal', 'one meal', 'generate a meal']
        }
        
        combined_text = (prompt + " " + system_message).lower()
        
        # Check for weekly plan indicators
        if any(indicator in combined_text for indicator in content_indicators['weekly']):
            logger.debug("Detected weekly plan generation - using high token limit")
            return 6000  # Reduced from 8000 for weekly plans
        
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
        try:
            # Direct JSON parsing (works with response_mime_type="application/json")
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Direct JSON parsing failed: {str(e)}")
            logger.debug(f"Content length: {len(content)} characters")
            
            # Try to fix common JSON issues
            cleaned_content = self._clean_json_content(content)
            if cleaned_content:
                try:
                    return json.loads(cleaned_content)
                except json.JSONDecodeError as e2:
                    logger.warning(f"Cleaned JSON parsing failed: {str(e2)}")
            
            # Fallback: try to find JSON in markdown code block
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                try:
                    json_content = json_match.group(1).strip()
                    return json.loads(json_content)
                except json.JSONDecodeError as e3:
                    logger.warning(f"Markdown JSON parsing failed: {str(e3)}")
            
            # Last resort: find any JSON-like structure
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    json_content = json_match.group(0)
                    cleaned_json = self._clean_json_content(json_content)
                    if cleaned_json:
                        return json.loads(cleaned_json)
                except json.JSONDecodeError as e4:
                    logger.warning(f"Regex JSON parsing failed: {str(e4)}")
            
            # Log the problematic content for debugging (truncated)
            content_preview = content[:500] + "..." if len(content) > 500 else content
            logger.error(f"Could not extract valid JSON from response. Preview: {content_preview}")
            raise ValueError(f"Could not extract valid JSON from response: {str(e)}")
    
    def _clean_json_content(self, content: str) -> str:
        """Clean common JSON formatting issues."""
        if not content.strip():
            return ""
        
        # Remove common problematic patterns
        content = content.strip()
        
        # Remove trailing commas before closing brackets/braces
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        
        # Fix missing quotes around keys (simple cases)
        content = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', content)
        
        # Remove any trailing content after the main JSON object
        brace_count = 0
        json_end = -1
        for i, char in enumerate(content):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i
                    break
        
        if json_end > 0:
            content = content[:json_end + 1]
        
        return content
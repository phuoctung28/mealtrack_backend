import base64
import json
import os
from typing import Dict, Any, List

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.strategies.meal_analysis_strategy import (
    MealAnalysisStrategy,
    AnalysisStrategyFactory
)

# Load environment variables
load_dotenv()

class VisionAIService(VisionAIServicePort):
    """
    Implementation of VisionAIServicePort using Google Gemini API.
    
    This class implements US-2.1 - Call Vision AI to get nutrition estimate.
    """
    
    def __init__(self):
        """Initialize the Gemini client."""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")
            
        self.model = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            temperature=0.2,
            max_output_tokens=1500,
            google_api_key=self.api_key,
            convert_system_message_to_human=True
        )
        
    def analyze_with_strategy(self, image_bytes: bytes, strategy: MealAnalysisStrategy) -> Dict[str, Any]:
        """
        Analyze a food image using the provided analysis strategy.
        
        Args:
            image_bytes: The raw bytes of the image to analyze
            strategy: The analysis strategy to use
            
        Returns:
            JSON-compatible dictionary with the raw AI response
            
        Raises:
            RuntimeError: If analysis fails
        """
        try:
            # Encode image for the API
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Create message with the image using strategy
            messages = [
                SystemMessage(content=strategy.get_analysis_prompt()),
                HumanMessage(
                    content=[
                        {"type": "text", "text": strategy.get_user_message()},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                )
            ]
            
            # Call the API
            response = self.model.invoke(messages)
            
            # Parse the response to extract the JSON
            content = response.content
            
            # Extract JSON from the response
            try:
                # Try to parse the entire response as JSON
                result = json.loads(content)
            except json.JSONDecodeError:
                # If that fails, try to find and extract just the JSON part
                import re
                json_match = re.search(r'```json(.*?)```', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1).strip()
                    result = json.loads(json_str)
                else:
                    # As a last resort, try to find any JSON-like structure
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        result = json.loads(json_str)
                    else:
                        raise ValueError("Could not extract JSON from response")
            
            return {
                "raw_response": content,
                "structured_data": result,
                "strategy_used": strategy.get_strategy_name()
            }
            
        except Exception as e:
            raise RuntimeError(f"Failed to analyze image with {strategy.get_strategy_name()}: {str(e)}")
        
    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze a food image to extract nutritional information.
        
        Args:
            image_bytes: The raw bytes of the image to analyze
            
        Returns:
            JSON-compatible dictionary with the raw AI response
            
        Raises:
            RuntimeError: If analysis fails
        """
        strategy = AnalysisStrategyFactory.create_basic_strategy()
        return self.analyze_with_strategy(image_bytes, strategy)
    
    def analyze_with_portion_context(self, image_bytes: bytes, portion_size: float, unit: str) -> Dict[str, Any]:
        """
        Analyze a food image with specific portion size context.
        
        Args:
            image_bytes: The raw bytes of the image to analyze
            portion_size: The target portion size
            unit: The unit of the portion size
            
        Returns:
            JSON-compatible dictionary with the raw AI response
        """
        strategy = AnalysisStrategyFactory.create_portion_strategy(portion_size, unit)
        return self.analyze_with_strategy(image_bytes, strategy)
    
    def analyze_with_ingredients_context(self, image_bytes: bytes, ingredients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a food image with known ingredients context.
        
        Args:
            image_bytes: The raw bytes of the image to analyze
            ingredients: List of ingredient dictionaries with name, quantity, unit
            
        Returns:
            JSON-compatible dictionary with the raw AI response
        """
        strategy = AnalysisStrategyFactory.create_ingredient_strategy(ingredients)
        return self.analyze_with_strategy(image_bytes, strategy)
    
    def analyze_with_weight_context(self, image_bytes: bytes, weight_grams: float) -> Dict[str, Any]:
        """
        Analyze a food image with specific weight context for accurate nutrition.
        
        Args:
            image_bytes: The raw bytes of the image to analyze
            weight_grams: The target weight in grams
            
        Returns:
            JSON-compatible dictionary with the raw AI response
        """
        strategy = AnalysisStrategyFactory.create_weight_strategy(weight_grams)
        return self.analyze_with_strategy(image_bytes, strategy) 
import base64
import json
import os
import re
from typing import Dict, Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from domain.ports.vision_ai_service_port import VisionAIServicePort
from domain.services.analysis_strategy import MealAnalysisStrategy, AnalysisStrategyFactory

# Load environment variables
load_dotenv()

class VisionAIService(VisionAIServicePort):
    """Google Gemini-based implementation of VisionAIServicePort."""
    
    def __init__(self):
        """Initialize the Gemini client."""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")
            
        self.model = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.2,
            max_output_tokens=1500,
            google_api_key=self.api_key,
            convert_system_message_to_human=True
        )
        
    def analyze(self, image_bytes: bytes, strategy=None) -> Dict[str, Any]:
        """Analyze food image using the provided strategy."""
        if strategy is None:
            strategy = AnalysisStrategyFactory.create_basic_strategy()
        
        return self._analyze_with_strategy(image_bytes, strategy)
        
    def _analyze_with_strategy(self, image_bytes: bytes, strategy: MealAnalysisStrategy) -> Dict[str, Any]:
        """Internal method to analyze image with strategy."""
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
            
            # Parse JSON from response
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                result = self._extract_json_from_text(content)
            
            return {
                "raw_response": content,
                "structured_data": result,
                "strategy_used": strategy.get_strategy_name()
            }
            
        except Exception as e:
            raise RuntimeError(f"Failed to analyze image with {strategy.get_strategy_name()}: {str(e)}")
    
    def _extract_json_from_text(self, content: str) -> Dict[str, Any]:
        """Extract JSON from text response."""
        # Try markdown JSON block
        json_match = re.search(r'```json(.*?)```', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1).strip())
        
        # Try any JSON-like structure
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        
        raise ValueError("Could not extract JSON from response") 
import os
import json
from typing import Dict, Any

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from domain.ports.vision_ai_service_port import VisionAIServicePort

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
            model="gemini-1.5-flash",
            temperature=0.2,
            max_output_tokens=1500,
            google_api_key=self.api_key,
            convert_system_message_to_human=True
        )
        
        self._setup_prompt()
        
    def _setup_prompt(self):
        """Set up the system prompt for analyzing food images."""
        self.system_prompt = """
        You are a nutrition analysis assistant that can analyze food in images.
        Examine the image carefully and provide detailed nutritional information.
        
        Return your analysis in the following JSON format:
        {
          "foods": [
            {
              "name": "Food name",
              "quantity": 1.0,
              "unit": "serving/g/oz/cup/etc",
              "calories": 100,
              "macros": {
                "protein": 10,
                "carbs": 20,
                "fat": 5,
                "fiber": 2
              }
            }
          ],
          "total_calories": 100,
          "confidence": 0.8
        }
        
        - Each food item should include name, estimated quantity, unit of measurement, calories, and macros
        - For quantities, estimate as precisely as possible based on visual cues
        - All macros should be in grams
        - Confidence should be between 0 (low) and 1 (high) based on how certain you are of your analysis
        - Always return well-formed JSON
        """
        
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
        try:
            # Encode image for the API
            import base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Create message with the image
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(
                    content=[
                        {"type": "text", "text": "Analyze this food image and provide nutritional information:"},
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
                "structured_data": result
            }
            
        except Exception as e:
            raise RuntimeError(f"Failed to analyze image: {str(e)}") 
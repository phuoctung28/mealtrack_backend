import gradio as gr
from typing import List, Tuple, Dict
import uuid
from datetime import datetime

# Simulated conversation flow for testing without the API
class MockMealPlanChatbot:
    def __init__(self):
        self.conversation_id = None
        self.state = "greeting"
        self.context = {}
        self.responses = {
            "greeting": "Hi there! 👋 I'd be happy to help you plan your meals. To get started, could you tell me your **dietary preferences or restrictions**? (For example: vegan, gluten-free, keto, etc.)",
            "dietary": "Got it – {dietary}. 👍 Next, do you have any **food allergies** I should know about?",
            "allergies": "Perfect. Now, what are your **health or fitness goals**? (For example: weight loss, muscle gain, maintenance...)",
            "fitness": "Great, thanks! I'll make sure to include appropriate meals for {goal}. How many **meals per day** would you like me to plan?",
            "meals": "Okay. And are we planning for **just one day or a full week** of meals?",
            "duration": "Excellent. I'll prepare a {duration} meal plan with {meals} meals and {snacks} snacks per day. One more thing: how much **time do you usually have to cook** each meal?",
            "cooking": "Understood. I'll keep weeknight recipes quick and use the weekends for anything that takes longer. 🤗 Lastly, any specific **ingredients or cuisines you love or want to avoid**?",
            "cuisine": "Thanks for the details! 🎉 Let's recap quickly: You want a {duration}, {dietary} **meal plan** with {meals} meals and {snacks} snacks per day. Your goal is {goal}. You have ~{cooking_time} minutes to cook on weeknights. Sound good?",
            "confirm": "Perfect! Give me a moment to generate your personalized meal plan... 🤖🍳",
            "plan": """Here's your **meal plan for the week**. I've organized it by day, with each meal tailored to your preferences and goals:

**Monday**
* **Breakfast:** Greek yogurt parfait with mixed berries and nuts – *A quick high-protein breakfast* (prep time ~5 min).
* **Snack 1:** Apple slices with almond butter.
* **Lunch:** Mediterranean quinoa salad with chickpeas and feta – *Gluten-free and vegetarian, packed with protein.*
* **Snack 2:** Protein smoothie.
* **Dinner:** Zucchini noodle "pasta" with marinara and vegetables – *Italian-style, gluten-free.*

**Tuesday**
* **Breakfast:** Veggie omelette with gluten-free toast.
* **Lunch:** Buddha bowl with tahini dressing.
* **Dinner:** Stuffed bell peppers with quinoa and beans.

*(...and similar meal listings for the rest of the week...)*

I've kept the recipes **simple for busy weekdays** and included some of your favorite flavors throughout the week. Let me know if anything doesn't look right or if you'd like to **adjust any specific meal**! 😊"""
        }
        
        # Suggested responses for each state
        self.suggestions = {
            "greeting": [
                "I'm vegetarian",
                "Gluten-free and vegan",
                "No dietary restrictions",
                "I follow a keto diet"
            ],
            "dietary": [
                "No allergies",
                "I'm allergic to nuts",
                "Dairy allergy",
                "Shellfish and eggs"
            ],
            "allergies": [
                "Weight loss",
                "Muscle gain",
                "Just maintaining my weight",
                "General health"
            ],
            "fitness": [
                "3 meals a day",
                "3 meals and 2 snacks",
                "2 meals and 1 snack",
                "4 small meals"
            ],
            "meals": [
                "Just one day",
                "A full week please",
                "Let's start with 3 days",
                "Weekly meal plan"
            ],
            "duration": [
                "30 minutes on weekdays",
                "15-20 minutes max",
                "I have plenty of time",
                "45 mins weekdays, more on weekends"
            ],
            "cooking": [
                "I love Italian food",
                "Asian cuisine, no tofu",
                "Mediterranean style",
                "No specific preferences"
            ],
            "cuisine": [
                "Yes, sounds perfect!",
                "That looks great",
                "Let me change something",
                "Confirmed!"
            ],
            "plan": [
                "Can you change Monday's dinner?",
                "I need more protein options",
                "Looks perfect, thank you!",
                "Save this plan"
            ]
        }
    
    def get_current_suggestions(self) -> List[str]:
        """Get suggestions for the current conversation state"""
        return self.suggestions.get(self.state, [])
    
    def start_new_conversation(self):
        """Start a new conversation"""
        self.conversation_id = str(uuid.uuid4())[:8]
        self.state = "greeting"
        self.context = {}
        return [(None, self.responses["greeting"])], f"Conversation started! (Demo mode)", gr.update(choices=self.get_current_suggestions(), value=None, visible=True)
    
    def process_message(self, message: str) -> Tuple[str, List[str]]:
        """Process user message and return appropriate response with suggestions"""
        message_lower = message.lower()
        
        if self.state == "greeting":
            # Parse dietary preferences
            dietary_prefs = []
            if "vegetarian" in message_lower:
                dietary_prefs.append("vegetarian")
            if "vegan" in message_lower:
                dietary_prefs.append("vegan")
            if "gluten" in message_lower:
                dietary_prefs.append("gluten-free")
            if "keto" in message_lower:
                dietary_prefs.append("keto")
            if not dietary_prefs and ("none" in message_lower or "no restriction" in message_lower):
                dietary_prefs = ["no restrictions"]
            
            self.context["dietary"] = ", ".join(dietary_prefs) if dietary_prefs else "your preferences"
            self.state = "dietary"
            return self.responses["dietary"].format(dietary=self.context["dietary"]), self.get_current_suggestions()
        
        elif self.state == "dietary":
            # Parse allergies
            self.context["allergies"] = "noted" if "no" not in message_lower else "none"
            self.state = "allergies"
            return self.responses["allergies"], self.get_current_suggestions()
        
        elif self.state == "allergies":
            # Parse fitness goals
            if "muscle" in message_lower or "gain" in message_lower:
                self.context["goal"] = "muscle gain"
            elif "loss" in message_lower or "lose" in message_lower:
                self.context["goal"] = "weight loss"
            elif "maintain" in message_lower:
                self.context["goal"] = "maintenance"
            else:
                self.context["goal"] = "general health"
            
            self.state = "fitness"
            return self.responses["fitness"].format(goal=self.context["goal"]), self.get_current_suggestions()
        
        elif self.state == "fitness":
            # Parse meal count
            import re
            numbers = re.findall(r'\d+', message)
            self.context["meals"] = int(numbers[0]) if numbers else 3
            self.context["snacks"] = int(numbers[1]) if len(numbers) > 1 else 0
            self.state = "meals"
            return self.responses["meals"], self.get_current_suggestions()
        
        elif self.state == "meals":
            # Parse duration
            self.context["duration"] = "weekly" if "week" in message_lower else "daily"
            self.state = "duration"
            return self.responses["duration"].format(
                duration=self.context["duration"],
                meals=self.context["meals"],
                snacks=self.context["snacks"]
            ), self.get_current_suggestions()
        
        elif self.state == "duration":
            # Parse cooking time
            import re
            numbers = re.findall(r'\d+', message)
            self.context["cooking_time"] = int(numbers[0]) if numbers else 30
            self.state = "cooking"
            return self.responses["cooking"], self.get_current_suggestions()
        
        elif self.state == "cooking":
            # Parse cuisine preferences
            self.context["cuisines"] = "your preferences"
            self.state = "cuisine"
            return self.responses["cuisine"].format(
                duration=self.context["duration"],
                dietary=self.context["dietary"],
                meals=self.context["meals"],
                snacks=self.context["snacks"],
                goal=self.context["goal"],
                cooking_time=self.context["cooking_time"]
            ), self.get_current_suggestions()
        
        elif self.state == "cuisine":
            # Handle confirmation
            if any(word in message_lower for word in ["yes", "yeah", "yep", "sure", "sounds good", "perfect", "confirmed"]):
                self.state = "confirm"
                # Auto-advance to plan
                self.state = "plan"
                return self.responses["confirm"] + "\n\n" + self.responses["plan"], self.get_current_suggestions()
            else:
                return "No problem! What would you like me to change?", []
        
        elif self.state == "plan":
            # Handle adjustments
            if "change" in message_lower or "adjust" in message_lower:
                return "I'll help you adjust that meal. Which specific meal would you like to change? (In a real system, I would regenerate that specific meal for you)", []
            else:
                return "Great! I'm glad you're happy with the meal plan. Enjoy your meals! 🥦💪", []
        
        return "I didn't quite understand that. Could you please rephrase?", self.get_current_suggestions()
    
    def send_message(self, message: str, history: List[Tuple[str, str]]):
        """Send a message to the chatbot"""
        if not message.strip():
            return history, "", gr.update()
        
        # Add user message to history
        history.append((message, ""))
        
        # Get response and suggestions
        response, suggestions = self.process_message(message)
        
        # Update history with response
        history[-1] = (message, response)
        
        # Return with updated suggestions
        return history, "", gr.update(choices=suggestions, value=None, visible=len(suggestions) > 0)

# Create the chatbot instance
chatbot = MockMealPlanChatbot()

# Create the Gradio interface
with gr.Blocks(title="MealTrack - Meal Plan Chatbot Demo", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🍽️ MealTrack Meal Planning Assistant (Demo)
    
    This is a demo of the meal planning chatbot with **suggested responses** to guide you through the conversation.
    Click on any suggestion or type your own response!
    
    Click **Start Conversation** to begin!
    """)
    
    with gr.Row():
        with gr.Column(scale=3):
            chatbot_ui = gr.Chatbot(
                label="Meal Planning Conversation",
                height=500,
                bubble_full_width=False,
                avatar_images=("🧑", "🤖")
            )
            
            # Suggested responses section
            with gr.Group():
                gr.Markdown("**💡 Suggested Responses:**")
                suggestions_radio = gr.Radio(
                    choices=[],
                    label="Click a suggestion or type your own message below",
                    visible=False,
                    elem_classes="suggestions-radio"
                )
            
            with gr.Row():
                msg = gr.Textbox(
                    label="Your message",
                    placeholder="Type your response here or select a suggestion above...",
                    lines=1,
                    scale=4
                )
                send_btn = gr.Button("Send", scale=1, variant="primary")
        
        with gr.Column(scale=1):
            start_btn = gr.Button("🚀 Start Conversation", variant="primary", size="lg")
            clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")
            
            gr.Markdown("""
            ### How it works:
            
            1. **Click Start Conversation**
            2. **Use suggested responses** or type your own
            3. **Follow the flow** through all questions
            4. **Get your meal plan!**
            
            ### Conversation Flow:
            1. 🎯 Dietary preferences
            2. 🥜 Allergies
            3. 💪 Fitness goals
            4. 🍽️ Meal count
            5. 📅 Plan duration
            6. ⏱️ Cooking time
            7. 🌮 Cuisine preferences
            8. ✅ Confirmation
            9. 📋 Meal plan display
            
            ### Features:
            - **Smart suggestions** at each step
            - **Natural language** understanding
            - **Personalized** meal plans
            - **Flexible** conversation flow
            """)
    
    # Add custom CSS for better styling
    demo.css = """
    .suggestions-radio {
        background-color: #f0f4f8;
        border-radius: 8px;
        padding: 10px;
    }
    .suggestions-radio label {
        display: inline-block;
        margin: 5px;
        padding: 8px 15px;
        background-color: white;
        border: 1px solid #ddd;
        border-radius: 20px;
        cursor: pointer;
        transition: all 0.3s;
    }
    .suggestions-radio label:hover {
        background-color: #e3f2fd;
        border-color: #2196f3;
    }
    .suggestions-radio input[type="radio"]:checked + label {
        background-color: #2196f3;
        color: white;
        border-color: #2196f3;
    }
    """
    
    # Connect the functions
    def start_conversation():
        history, status, suggestions = chatbot.start_new_conversation()
        return history, status, suggestions, ""
    
    start_btn.click(
        fn=start_conversation,
        outputs=[chatbot_ui, msg, suggestions_radio, msg]
    )
    
    clear_btn.click(
        fn=lambda: ([], "", gr.update(choices=[], visible=False), ""),
        outputs=[chatbot_ui, msg, suggestions_radio, msg]
    )
    
    # Handle suggestion selection
    def use_suggestion(suggestion):
        if suggestion:
            return suggestion
        return ""
    
    suggestions_radio.change(
        fn=use_suggestion,
        inputs=[suggestions_radio],
        outputs=[msg]
    )
    
    # Handle sending messages
    def send_and_update(message, history):
        new_history, _, suggestions = chatbot.send_message(message, history)
        return new_history, "", suggestions
    
    msg.submit(
        fn=send_and_update,
        inputs=[msg, chatbot_ui],
        outputs=[chatbot_ui, msg, suggestions_radio]
    )
    
    send_btn.click(
        fn=send_and_update,
        inputs=[msg, chatbot_ui],
        outputs=[chatbot_ui, msg, suggestions_radio]
    )
    
    # Add footer
    gr.Markdown("""
    ---
    ### 💡 Pro Tips:
    - You can **mix and match** the suggestions with your own text
    - The chatbot understands **natural language**, so feel free to be conversational
    - If you make a mistake, just **clarify** in your next message
    - The meal plan will be **customized** based on all your preferences
    
    This demo simulates the real MealTrack chatbot behavior with suggested responses for easier interaction!
    """)

if __name__ == "__main__":
    print("Starting MealTrack Meal Planning Chatbot Demo with Suggestions...")
    print("This enhanced demo includes clickable suggestion buttons for easier interaction.")
    print("Opening browser...")
    demo.launch(
        server_name="127.0.0.1",
        server_port=7861,
        share=False,
        inbrowser=True
    )
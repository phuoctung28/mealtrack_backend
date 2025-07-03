import gradio as gr
import requests
import json
from typing import List, Tuple

# Base URL for the API
BASE_URL = "http://localhost:8000"

class MealPlanChatbot:
    def __init__(self):
        self.conversation_id = None
        self.chat_history = []
    
    def start_new_conversation(self):
        """Start a new conversation"""
        try:
            response = requests.post(f"{BASE_URL}/v1/meal-plans/conversations/start?user_id=gradio_user")
            if response.status_code == 200:
                data = response.json()
                self.conversation_id = data["conversation_id"]
                self.chat_history = []
                assistant_msg = data["assistant_message"]
                self.chat_history.append(("", assistant_msg))
                return self.chat_history, f"Conversation started! ID: {self.conversation_id[:8]}..."
            else:
                return self.chat_history, f"Error starting conversation: {response.status_code}"
        except Exception as e:
            return self.chat_history, f"Error: {str(e)}"
    
    def send_message(self, message: str, history: List[Tuple[str, str]]):
        """Send a message to the chatbot"""
        if not self.conversation_id:
            # Start a new conversation if none exists
            self.start_new_conversation()
        
        if not message.strip():
            return history, ""
        
        try:
            # Add user message to history
            history.append((message, ""))
            
            # Send message to API
            response = requests.post(
                f"{BASE_URL}/v1/meal-plans/conversations/{self.conversation_id}/messages",
                json={"message": message}
            )
            
            if response.status_code == 200:
                data = response.json()
                assistant_msg = data["assistant_message"]
                
                # Update the last message with the assistant's response
                history[-1] = (message, assistant_msg)
                
                # Check if meal plan was generated
                if data.get("meal_plan_id"):
                    history.append(("", f"✅ Meal plan generated! ID: {data['meal_plan_id'][:8]}..."))
                
                return history, ""
            else:
                error_msg = f"Error: {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg += f" - {error_data.get('detail', response.text)}"
                    except:
                        error_msg += f" - {response.text}"
                history[-1] = (message, error_msg)
                return history, ""
                
        except Exception as e:
            history[-1] = (message, f"Error: {str(e)}")
            return history, ""
    
    def clear_conversation(self):
        """Clear the current conversation"""
        self.conversation_id = None
        self.chat_history = []
        return [], "Conversation cleared. Click 'Start New Conversation' to begin."

# Create the chatbot instance
chatbot = MealPlanChatbot()

# Create the Gradio interface
with gr.Blocks(title="MealTrack - Meal Plan Chatbot") as demo:

    with gr.Row():
        with gr.Column(scale=4):
            chatbot_ui = gr.Chatbot(
                label="Meal Planning Assistant",
                height=500,
                bubble_full_width=False
            )
            
            with gr.Row():
                msg = gr.Textbox(
                    label="Your message",
                    placeholder="Type your response here...",
                    lines=1,
                    scale=4
                )
                send_btn = gr.Button("Send", scale=1, variant="primary")
        
        with gr.Column(scale=1):
            status = gr.Textbox(
                label="Status",
                value="Click 'Start New Conversation' to begin",
                lines=2,
                interactive=False
            )
            
            start_btn = gr.Button("Start New Conversation", variant="primary", size="lg")
            clear_btn = gr.Button("Clear", variant="secondary", size="lg")
    
    # Connect the functions
    start_btn.click(
        fn=lambda: chatbot.start_new_conversation(),
        outputs=[chatbot_ui, status]
    )
    
    clear_btn.click(
        fn=lambda: chatbot.clear_conversation(),
        outputs=[chatbot_ui, status]
    )
    
    # Handle sending messages
    def send_message(message, history):
        new_history, _ = chatbot.send_message(message, history)
        return new_history, ""
    
    msg.submit(
        fn=send_message,
        inputs=[msg, chatbot_ui],
        outputs=[chatbot_ui, msg]
    )
    
    send_btn.click(
        fn=send_message,
        inputs=[msg, chatbot_ui],
        outputs=[chatbot_ui, msg]
    )

if __name__ == "__main__":
    print("Starting MealTrack Meal Planning Chatbot UI...")
    print("Make sure your API server is running at http://localhost:8000")
    print("Opening browser...")
    demo.launch(
        server_port=5000,
        share=False,
        inbrowser=True
    )
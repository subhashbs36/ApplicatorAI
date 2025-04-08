from pathlib import Path
import os
import re
import time
import google.generativeai as genai

class ChatbotGenerator:
    """Class for generating chat responses for job application assistance"""
    
    def __init__(self):
        """Initialize the chatbot generator"""
        self.base_path = Path(__file__).parent.parent.parent.parent
        self.data_path = self.base_path / "src" / "data"
        self.responses_path = self.data_path / "responses"
        self.chat_logs_path = self.responses_path / "chat_logs"
        self.chat_history = []
        
        # Ensure directory exists
        self.chat_logs_path.mkdir(parents=True, exist_ok=True)

    def save_chat_history(self, chat_history, company_name, position_name):
        """Save the chat history to a text file"""
        if not chat_history or len(chat_history) == 0:
            return "No chat history to save."
        
        # Clean file names for safety
        clean_company = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
        clean_position = re.sub(r'[^\w\s-]', '', position_name).strip().replace(' ', '_')
        timestamp = time.strftime("%Y%m%d%H%M%S")
        file_name = f"Chat_History_{clean_company}_{clean_position}_{timestamp}.txt"
        
        file_path = self.chat_logs_path / file_name
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for message in chat_history:
                    # Each message is a dictionary with role and content
                    role = message.get("role", "Unknown")
                    content = message.get("content", "")
                    f.write(f"{role}: {content}\n\n")
            return str(file_path)
        except Exception as e:
            print(f"Error creating file: {e}")
            return f"Error saving chat history: {str(e)}"
    
    def generate_response(self, user_message, job_description=None, resume_content=None, company_name=None, position_name=None):
        """Generate a response to the user's message"""
        if not user_message:
            return "Please provide a message to respond to."
        
        # Add context about the job if available
        job_context = ""
        if job_description:
            job_context += f"\nJob Description: {job_description[:1000]}"
        if company_name:
            job_context += f"\nCompany: {company_name}"
        if position_name:
            job_context += f"\nPosition: {position_name}"
        if resume_content:
            job_context += f"\nResume Highlights: {resume_content[:500]}"
        
        # Store the conversation history for context
        history_context = ""
        if self.chat_history:
            history_context = "\nPrevious conversation:\n"
            # Include up to the last 5 exchanges for context
            for message in self.chat_history[-10:]:
                history_context += f"{message['role']}: {message['content']}\n"
        
        # Generate the response using Gemini
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
        You are a helpful job application assistant. Your goal is to help the user with their job application process.
        
        {job_context}
        
        {history_context}
        
        User's current message: {user_message}
        
        Provide a helpful, concise, and informative response. Focus on practical advice related to:
        - Job application strategies
        - Interview preparation
        - Resume and cover letter optimization
        - Highlighting relevant skills for the position
        - Professional communication
        
        If the job details are available, tailor your advice to the specific position and company.
        If you don't know something, admit it rather than making up information.
        
        Format your response in two parts:
        1. Main Content: The primary response or template
        2. Additional Notes: Any tips, instructions, or follow-up questions (if applicable)
        
        Separate these parts with a clear delimiter: "---ADDITIONAL NOTES---"
        """
        
        try:
            response = model.generate_content(prompt)
            bot_response = response.text
            
            # Split the response into main content and additional notes
            parts = bot_response.split("---ADDITIONAL NOTES---")
            main_content = parts[0].strip()
            additional_notes = parts[1].strip() if len(parts) > 1 else ""
            
            # Update chat history with the main content only
            self.chat_history.append({"role": "user", "content": user_message})
            self.chat_history.append({"role": "assistant", "content": main_content})
            
            # Return both parts
            return {
                "main_content": main_content,
                "additional_notes": additional_notes
            }
        except Exception as e:
            error_message = f"Error generating response: {str(e)}"
            self.chat_history.append({"role": "user", "content": user_message})
            self.chat_history.append({"role": "assistant", "content": error_message})
            return {
                "main_content": error_message,
                "additional_notes": ""
            }
    
    def clear_history(self):
        """Clear the chat history"""
        self.chat_history = []
        return "Chat history cleared."
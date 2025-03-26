import os
import re
import time
import google.generativeai as genai
from pathlib import Path

class AiMailGenerator:
    """Class to generate AI-powered emails"""
    
    def __init__(self):
        """Initialize the generator"""
        self.base_path = Path(__file__).parent.parent.parent.parent
        self.data_path = self.base_path / "src" / "data"
        self.responses_path = self.data_path / "responses"
        self.ai_mails_path = self.responses_path / "ai_mails"
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.temp_email = None
        
        # Ensure directory exists
        self.ai_mails_path.mkdir(parents=True, exist_ok=True)

    def save_ai_mail(self, email_content, company_name, position_name):
        """Save the AI-generated email to a text file"""
        if not email_content:
            return None
        
        # Clean file names for safety
        clean_company = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
        clean_position = re.sub(r'[^\w\s-]', '', position_name).strip().replace(' ', '_')
        timestamp = time.strftime("%Y%m%d%H%M%S")
        
        # Create file path
        file_name = f"AI_Email_{clean_company}_{clean_position}_{timestamp}.txt"
        file_path = self.ai_mails_path / file_name
        
        # Write to file
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(email_content)
            return str(file_path)
        except Exception as e:
            print(f"Error saving AI email: {e}")
            return None
    
    def generate_email(self, description, context, company_name=None, position_name=None):
        """Generate an email based on the provided description and context"""
        if not description or not context:
            return "Error: Missing description or context."
        
        # Create prompt for the model
        prompt = f"""
        You are a professional email writer. Generate a well-crafted email based on the following:

        EMAIL PURPOSE:
        {description}

        CONTEXT TO CONSIDER:
        {context}

        {f'COMPANY: {company_name}' if company_name else ''}
        {f'POSITION: {position_name}' if position_name else ''}

        Guidelines for the email:
        1. Use a clear and appropriate subject line
        2. Maintain a professional tone while being engaging
        3. Be concise and focused on the main purpose
        4. Include relevant details from the provided context
        5. Use proper email structure (greeting, body, closing)
        6. Ensure proper formatting and paragraph breaks
        7. Keep the language natural and authentic
        8. End with a clear call to action if appropriate

        Write only the email content, including the subject line, without any explanations or notes.
        """

        try:
            response = self.model.generate_content(prompt)
            email_content = response.text.strip()
            
            # Store the generated email
            self.temp_email = email_content
            
            return email_content
        except Exception as e:
            return f"Error generating email: {str(e)}"
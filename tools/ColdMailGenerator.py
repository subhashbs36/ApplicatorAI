import os
import re
import time
import google.generativeai as genai

class ColdMailGenerator:
    """Class for generating cold emails to hiring managers"""
    
    def __init__(self):
        """Initialize the cold mail generator"""
        self.temp_cold_mail = None
        os.makedirs("cold_mails", exist_ok=True)
    
    def generate_cold_mail(self, resume_content, job_description, hr_name, company_name, position_name):
        """Generate a cold mail to a hiring manager"""
        if not resume_content or not job_description:
            return "Please provide resume content and job description."
        
        if not company_name or not position_name:
            return "Please provide both company name and position title."
        
        # Format HR name (use "Hiring Manager" if not provided)
        greeting_name = hr_name.strip() if hr_name and hr_name.strip() else "Hiring Manager"
        
        # Generate the cold mail using Gemini
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
        Create a professional cold email to send to a hiring manager or recruiter.
        
        Resume highlights:
        {resume_content[:1000]}  # Using first 1000 chars of resume for brevity
        
        Job details:
        Position: {position_name}
        Company: {company_name}
        Job Description Highlights: {job_description[:1000]}  # Using first 1000 chars
        
        The email should:
        1. Be addressed to {greeting_name}
        2. Be concise (150-200 words)
        3. Express interest in the {position_name} position
        4. Highlight 2-3 relevant qualifications from my resume that match the job
        5. Include a call to action (request for interview/conversation)
        6. Have a professional tone
        7. Include appropriate subject line and email signature
        
        Format as a complete email with subject line, greeting, body, and signature.
        """
        
        try:
            response = model.generate_content(prompt)
            cold_mail = response.text
            self.temp_cold_mail = cold_mail
            return cold_mail
        except Exception as e:
            return f"Error generating cold mail: {str(e)}"
    
    def save_cold_mail(self, cold_mail, company_name, position_name):
        """Save the cold mail to a text file"""
        if not cold_mail or cold_mail.startswith("Please ") or cold_mail.startswith("Error"):
            return None
        
        # Clean file names for safety
        clean_company = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
        clean_position = re.sub(r'[^\w\s-]', '', position_name).strip().replace(' ', '_')
        timestamp = time.strftime("%Y%m%d%H%M%S")
        file_name = f"Cold_Mail_{clean_company}_{clean_position}_{timestamp}.txt"
        
        file_path = os.path.join("cold_mails", file_name)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(cold_mail)
            return file_path
        except Exception as e:
            print(f"Error creating file: {e}")
            return None
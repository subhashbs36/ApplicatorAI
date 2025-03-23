import os
import re
import time
import google.generativeai as genai

class LinkedInDMGenerator:
    """Class for generating LinkedIn direct messages to hiring managers"""
    
    def __init__(self):
        """Initialize the LinkedIn DM generator"""
        self.temp_linkedin_dm = None
        os.makedirs("linkedin_dms", exist_ok=True)
    
    def generate_linkedin_dm(self, resume_content, job_description, hr_name, company_name, position_name):
        """Generate a LinkedIn DM to a hiring manager"""
        if not resume_content or not job_description:
            return "Please provide resume content and job description."
        
        if not company_name or not position_name:
            return "Please provide both company name and position title."
        
        # Format HR name (use appropriate default if not provided)
        greeting_name = hr_name.strip() if hr_name and hr_name.strip() else ""
        
        # Generate the LinkedIn DM using Gemini
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
        Create a brief, professional LinkedIn direct message to a hiring manager or recruiter.
        
        Resume highlights:
        {resume_content[:800]}  # Using first 800 chars of resume for brevity
        
        Job details:
        Position: {position_name}
        Company: {company_name}
        
        The message should:
        1. {f"Be addressed to {greeting_name}" if greeting_name else "Have an appropriate greeting"}
        2. Be very concise (maximum 100 words)
        3. Express interest in the {position_name} position
        4. Mention 1-2 key qualifications relevant to the role
        5. Include a brief call to action
        6. Be conversational but professional
        
        Format as a complete LinkedIn message that's ready to send.
        """
        
        try:
            response = model.generate_content(prompt)
            linkedin_dm = response.text
            self.temp_linkedin_dm = linkedin_dm
            return linkedin_dm
        except Exception as e:
            return f"Error generating LinkedIn DM: {str(e)}"
    
    def save_linkedin_dm(self, linkedin_dm, company_name, position_name):
        """Save the LinkedIn DM to a text file"""
        if not linkedin_dm or linkedin_dm.startswith("Please ") or linkedin_dm.startswith("Error"):
            return None
        
        # Clean file names for safety
        clean_company = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
        clean_position = re.sub(r'[^\w\s-]', '', position_name).strip().replace(' ', '_')
        timestamp = time.strftime("%Y%m%d%H%M%S")
        file_name = f"LinkedIn_DM_{clean_company}_{clean_position}_{timestamp}.txt"
        
        file_path = os.path.join("linkedin_dms", file_name)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(linkedin_dm)
            return file_path
        except Exception as e:
            print(f"Error creating file: {e}")
            return None
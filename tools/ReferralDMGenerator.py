import os
import re
import time
import google.generativeai as genai

class ReferralDMGenerator:
    """Class to generate LinkedIn DMs for referral requests"""
    
    def __init__(self):
        """Initialize the generator"""
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.temp_referral_dm = None
    
    def generate_referral_dm(self, resume_content, job_description, referral_name, company_name, position_name):
        """Generate a LinkedIn DM to request a referral"""
        if not resume_content or not job_description:
            return "Error: Missing resume or job description."
        
        if not company_name or not position_name:
            return "Error: Missing company name or position title."
        
        if not referral_name:
            return "Error: Please provide the name of your connection to personalize the message."
        
        # Create prompt for the model
        prompt = f"""
        You are a professional job seeker looking to request a referral from a connection on LinkedIn.

        Based on the following resume and job description, craft a concise, professional LinkedIn message to {referral_name} 
        who works at {company_name}, asking for a referral for the {position_name} position.

        The message should:
        1. Start with a warm, personalized greeting
        2. Be friendly but professional in tone
        3. Briefly mention your relevant experience that matches the job (highlight 2-3 key qualifications)
        4. Express genuine interest in the role and company with specific details about why you're interested
        5. Politely ask if they would be willing to refer you or provide insights about the company culture
        6. Thank them for their consideration and time
        7. End with a professional closing
        8. Be under 300 words (LinkedIn message limit)
        9. Use natural, conversational language that builds rapport

        RESUME:
        {resume_content}

        JOB DESCRIPTION:
        {job_description}

        Write only the message content, without any explanations or notes.
        """

        try:
            response = self.model.generate_content(prompt)
            referral_dm = response.text.strip()
            
            # Store the generated message
            self.temp_referral_dm = referral_dm
            
            return referral_dm
        except Exception as e:
            return f"Error generating referral request: {str(e)}"
    
    def save_referral_dm(self, referral_dm, company_name, position_name):
        """Save the referral DM to a text file"""
        if not referral_dm:
            return None
        
        # Clean file names for safety
        clean_company = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
        clean_position = re.sub(r'[^\w\s-]', '', position_name).strip().replace(' ', '_')
        timestamp = time.strftime("%Y%m%d%H%M%S")
        
        # Create directory if it doesn't exist
        os.makedirs("referral_messages", exist_ok=True)
        
        # Create file path
        file_name = f"Referral_Request_{clean_company}_{clean_position}_{timestamp}.txt"
        file_path = os.path.join("referral_messages", file_name)
        
        # Write to file
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(referral_dm)
            return file_path
        except Exception as e:
            print(f"Error saving referral message: {e}")
            return None
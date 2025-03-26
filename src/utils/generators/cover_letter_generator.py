import hashlib
import json
import os
import time
import re
from datetime import date
import google.generativeai as genai
from pathlib import Path


# Constants
MAX_TOKEN_LENGTH = 8000  # Adjust based on model limits
CACHE_EXPIRY = 60


class CoverLetterGenerator:
    """Class to handle cover letter generation operations"""
    
    def __init__(self):
        self.model_name = 'gemini-2.0-flash'
        self.base_path = Path(__file__).parent.parent.parent.parent
        self.data_path = self.base_path / "src" /"data"
        self.cache_path = self.data_path / "cache"
        
        # Ensure cache directory exists
        self.cache_path.mkdir(parents=True, exist_ok=True)
    
    def check_cache(self, cache_key):
        """Check if there's a cached response for this query"""
        cache_file = self.cache_path / f"{cache_key}.json"
        
        if cache_file.exists():
            # Check if cache is expired
            file_age = time.time() - cache_file.stat().st_mtime
            if file_age < CACHE_EXPIRY:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    return cache_data.get('cover_letter')
                except Exception:
                    # If cache read fails, ignore and regenerate
                    pass
        return None
    
    def save_to_cache(self, cache_key, cover_letter):
        """Save the generated cover letter to cache"""
        cache_file = self.cache_path / f"{cache_key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'cover_letter': cover_letter, 'timestamp': time.time()}, f)
        except Exception as e:
            print(f"Cache saving error: {str(e)}")
    
    def truncate_text(self, text, max_chars=MAX_TOKEN_LENGTH):
        """Truncate text to stay within token limits"""
        if len(text) <= max_chars:
            return text
        
        # More intelligent truncation that tries to preserve key resume sections
        # Look for section headers and preserve the most relevant ones
        sections = re.split(r'\n\s*\n|\r\n\s*\r\n', text)
        
        important_keywords = ['experience', 'education', 'skills', 'projects', 'publications']
        prioritized_sections = []
        other_sections = []
        
        for section in sections:
            if any(keyword.lower() in section.lower() for keyword in important_keywords):
                prioritized_sections.append(section)
            else:
                other_sections.append(section)
        
        # Combine sections up to the max length limit
        result = ""
        remaining_chars = max_chars - 50  # leave some buffer
        
        # First add prioritized sections
        for section in prioritized_sections:
            if len(section) + len(result) < remaining_chars:
                result += section + "\n\n"
            else:
                # If section is too long, truncate it
                available_space = remaining_chars - len(result)
                if available_space > 100:  # Only add if we have meaningful space
                    result += section[:available_space] + "...\n\n"
                break
        
        # Then add other sections if space remains
        for section in other_sections:
            if len(section) + len(result) < remaining_chars:
                result += section + "\n\n"
            else:
                break
        
        return result.strip() + "\n...[content intelligently truncated to fit token limits]"
    
    def generate_cover_letter(self, resume_content, job_description, company_name, position_name):
        """Generate cover letter using Gemini API"""
        # Input validation
        for input_name, input_value in [
            ("resume", resume_content),
            ("job description", job_description),
            ("company name", company_name),
            ("position name", position_name)
        ]:
            if not input_value or input_value.strip() == "":
                return f"Please provide a valid {input_name}."
        
        # Prepare data
        today = date.today().strftime("%B %d, %Y")
        
        # Use provided content directly
        processed_resume = resume_content
        processed_job = job_description       

        # Create the prompt for Gemini
        prompt = f"""
        You are a professional cover letter writer. Based on the resume and job description provided, create a compelling and onpoint cover letter.
        
        Resume:
        {processed_resume}
        
        Job Description:
        {processed_job}
        
        Create a cover letter for a {position_name} position at {company_name} with the following structure:
        
        1. Start with today's date ({today})
        2. Include "Hiring Manager" and {company_name} in the header
        3. Begin with "Dear Hiring Manager,"
        4. Write a compelling opening paragraph that specifically mentions the {position_name} position at {company_name}
        5. In the body paragraphs, directly connect 3-4 specific achievements from the resume to the requirements in the job description which is from Linkedin
        6. Explain specifically why the candidate is interested in {company_name} (research their mission or recent projects)
        7. Include a strong closing paragraph with contact information from the resume
        8. End with "Sincerely," followed by the full name from the resume
        
        The cover letter should be professional, Natural, concise yet comprehensive (around 300-400 words), and highlight the most relevant experiences and skills from the resume that match the job description.
        
        DO NOT include any links, placeholder text or instructions in the final cover letter.
        """
        
        try:
            # Initialize Gemini model with system message to improve quality
            model = genai.GenerativeModel(self.model_name, 
                                        generation_config={
                                            "temperature": 0.7,
                                            "top_p": 0.9,
                                            "top_k": 40
                                        })
            
            # Generate the cover letter
            response = model.generate_content(prompt)
            
            # Process the response
            cover_letter = response.text.strip()
            
            # Post-processing to ensure proper formatting
            cover_letter = self.post_process_letter(cover_letter, today, company_name)
            
            return cover_letter
        
        except Exception as e:
            error_message = str(e)
            return f"Error generating cover letter: {error_message}"
    

    def post_process_letter(self, cover_letter, today, company_name):
        """Format the cover letter to ensure it meets the requirements"""
        # Ensure the date is included at the top
        if today not in cover_letter[:100]:
            cover_letter = today + "\n\n" + cover_letter
        
        # Ensure company name is included in header
        if company_name not in cover_letter[:250]:
            match = re.search(r'Dear .+,', cover_letter)
            if match:
                idx = match.start()
                header_section = cover_letter[:idx].strip()
                if "Hiring Manager" not in header_section:
                    # Insert company name and "Hiring Manager" before salutation
                    cover_letter = today + "\n\nHiring Manager\n" + company_name + "\n\n" + cover_letter[idx:]
        
        # Fix any doubled salutations or dates
        cover_letter = re.sub(r'('+today+r')\s*\n\s*('+today+r')', r'\1', cover_letter)
        cover_letter = re.sub(r'(Dear Hiring Manager,)\s*\n\s*(Dear Hiring Manager,)', r'\1', cover_letter)
        
        return cover_letter
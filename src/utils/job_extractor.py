import google.generativeai as genai
from typing import Dict

class JobDetailsExtractor:
    def __init__(self):
        self.model_name = 'gemini-2.0-flash'
        
    def extract_from_text(self, text: str) -> Dict[str, str]:
        """Extract job details from text using AI"""
        if not text or text.strip() == "":
            return {'company': 'Unknown', 'position': 'Unknown'}

        # Clean the text to remove problematic patterns
        cleaned_text = text
        if '+ 5 more' in text:
            cleaned_text = text.replace('+ 5 more', '')

        prompt = f"""
        Extract the company name and complete job position from the following job description.
        Return ONLY these two pieces of information in the following format:
        Company: [company name]
        Position: [position title]

        If you cannot find either piece of information, use "Unknown" as the value.
        
        Job Description:
        {cleaned_text}
        """

        try:
            # Initialize Gemini model
            model = genai.GenerativeModel(
                self.model_name,
                generation_config={
                    "temperature": 0.1,  # Lower temperature for more focused extraction
                    "top_p": 0.9,
                    "top_k": 40
                }
            )

            # Generate the extraction
            response = model.generate_content(prompt)
            
            # Parse the response
            response_text = response.text.strip()
            
            # Extract company and position using string parsing
            company = "Unknown"
            position = "Unknown"
            
            for line in response_text.split('\n'):
                if line.lower().startswith('company:'):
                    company = line.split(':', 1)[1].strip()
                elif line.lower().startswith('position:'):
                    position = line.split(':', 1)[1].strip()

            # Add additional logging for debugging
            print(f"Extracted - Company: {company}, Position: {position}")

            return {
                'company': company if company != "Unknown" else "",
                'position': position if position != "Unknown" else ""
            }

        except Exception as e:
            print(f"Error extracting job details: {str(e)}")
            # Try a fallback approach for LinkedIn URLs
            if "linkedin.com/jobs" in text:
                try:
                    # Simple regex-based extraction for LinkedIn
                    import re
                    company_match = re.search(r'Company Name:\s*([^\n]+)', text)
                    position_match = re.search(r'Job Title:\s*([^\n]+)', text)
                    
                    company = company_match.group(1).strip() if company_match else ""
                    position = position_match.group(1).strip() if position_match else ""
                    
                    print(f"Fallback extraction - Company: {company}, Position: {position}")
                    return {'company': company, 'position': position}
                except Exception as fallback_error:
                    print(f"Fallback extraction failed: {str(fallback_error)}")
            
            return {'company': '', 'position': ''}
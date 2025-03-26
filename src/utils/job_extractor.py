import google.generativeai as genai
from typing import Dict

class JobDetailsExtractor:
    def __init__(self):
        self.model_name = 'gemini-2.0-flash'
        
    def extract_from_text(self, text: str) -> Dict[str, str]:
        """Extract job details from text using AI"""
        if not text or text.strip() == "":
            return {'company': '', 'position': ''}

        prompt = f"""
        Extract the company name and complete job position from the following job description.
        Return ONLY these two pieces of information in the following format:
        Company: [company name]
        Position: [position title]

        If you cannot find either piece of information, use "Unknown" as the value.
        
        Job Description:
        {text}
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
            response = model.generate_content(prompt.format(text=text))
            
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

            return {
                'company': company if company != "Unknown" else "",
                'position': position if position != "Unknown" else ""
            }

        except Exception as e:
            print(f"Error extracting job details: {str(e)}")
            return {'company': '', 'position': ''}
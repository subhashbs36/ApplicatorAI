from datetime import date
import google.generativeai as genai
import hashlib
import os
import re
import time
import json


CACHE_EXPIRY = 60  


class JobApplicationQnA:
    """Class to handle job application Q&A operations"""
    
    def __init__(self):
        self.model_name = 'gemini-2.0-flash'
        
    def generate_answer(self, resume_content, job_description, question, company_name, position_name, word_limit=None):
        """Generate answer to a job application question using Gemini API"""
        # Input validation
        for input_name, input_value in [
            ("resume", resume_content),
            ("job description", job_description),
            ("question", question),
            ("company name", company_name),
            ("position name", position_name)
        ]:
            if not input_value or input_value.strip() == "":
                return f"Please provide a valid {input_name}."
        
        # Create the cache key
        cache_key = self.get_cache_key(resume_content, job_description, question, company_name, position_name, word_limit)
        
        # Check cache for existing response
        cached_response = self.check_cache(cache_key)
        if cached_response:
            return cached_response
            
        # Create the prompt for Gemini
        prompt = f"""
        You are a professional job application specialist. Your task is to help a candidate create a personalized answer to a job application question.
        
        Resume:
        {resume_content}
        
        Job Description:
        {job_description}
        
        Position: {position_name} at {company_name}
        
        Job Application Question: "{question}"
        
        {f'Word Limit: {word_limit} words' if word_limit else ''}
        
        Write a compelling, specific, and personalized answer to this question that:
        1. Directly addresses what the question is asking
        2. Connects relevant experiences from the resume to the job requirements
        3. Uses specific examples and metrics from the resume when possible
        4. Aligns with the company's values or requirements from the job description
        5. Shows enthusiasm for this specific role and company
        6. Is concise, professional, and conversational in tone
        7. Avoids generic answers that could apply to any company
        8. If there is a word limit, respect it exactly
        
        The answer should sound natural and personal, as if the candidate wrote it themselves.
        DO NOT include any explanatory text, just provide the answer itself.
        """
        
        try:
            # Initialize Gemini model
            model = genai.GenerativeModel(self.model_name, 
                                        generation_config={
                                            "temperature": 0.7,
                                            "top_p": 0.9,
                                            "top_k": 40
                                        })
            
            # Generate the answer
            response = model.generate_content(prompt)
            
            # Process the response
            answer = response.text.strip()
            
            # Post-processing to ensure proper formatting and word count
            if word_limit:
                answer = self.ensure_word_limit(answer, word_limit)
            
            # Save to cache
            self.save_to_cache(cache_key, answer)
            
            return answer
        
        except Exception as e:
            error_message = str(e)
            return f"Error generating answer: {error_message}"
    
    def ensure_word_limit(self, text, word_limit):
        """Ensure the text respects the word limit"""
        words = text.split()
        if len(words) <= word_limit:
            return text
            
        # Truncate to word limit and add ellipsis
        return " ".join(words[:word_limit])
    
    @staticmethod
    def get_cache_key(resume_content, job_description, question, company_name, position_name, word_limit):
        """Generate a unique cache key for the current inputs"""
        data = f"{resume_content}|{job_description}|{question}|{company_name}|{position_name}|{word_limit}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def check_cache(self, cache_key):
        """Check if there's a cached response for this query"""
        cache_file = os.path.join("cache", f"qna_{cache_key}.json")
        
        if os.path.exists(cache_file):
            # Check if cache is expired
            file_age = time.time() - os.path.getmtime(cache_file)
            if file_age < CACHE_EXPIRY:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    return cache_data.get('answer')
                except Exception:
                    # If cache read fails, ignore and regenerate
                    pass
        return None
    
    def save_to_cache(self, cache_key, answer):
        """Save the generated answer to cache"""
        cache_file = os.path.join("cache", f"qna_{cache_key}.json")
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'answer': answer, 'timestamp': time.time()}, f)
        except Exception as e:
            print(f"Cache saving error: {str(e)}")
    
    def save_qna_response(self, questions_answers, company_name, position_name):
        """Save the Q&A responses to a text file"""
        # Clean file names for safety
        clean_company = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
        clean_position = re.sub(r'[^\w\s-]', '', position_name).strip().replace(' ', '_')
        timestamp = time.strftime("%Y%m%d%H%M%S")
        file_name = f"QnA_Responses_{clean_company}_{clean_position}_{timestamp}.txt"
        
        os.makedirs("qna_responses", exist_ok=True)
        file_path = os.path.join("qna_responses", file_name)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Job Application Responses\n")
                f.write(f"Position: {position_name} at {company_name}\n")
                f.write(f"Date: {date.today().strftime('%B %d, %Y')}\n\n")
                
                for q, a in questions_answers:
                    f.write(f"Question: {q}\n\n")
                    f.write(f"Answer: {a}\n\n")
                    f.write("-" * 50 + "\n\n")
            
            return file_path
        except Exception as e:
            print(f"Error saving Q&A responses: {e}")
            return None
    
    def save_custom_qna(self, custom_content, company_name, position_name):
        """Save custom Q&A content to a file"""
        # Clean file names for safety
        clean_company = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
        clean_position = re.sub(r'[^\w\s-]', '', position_name).strip().replace(' ', '_')
        timestamp = time.strftime("%Y%m%d%H%M%S")
        file_name = f"QnA_{clean_company}_{clean_position}_{timestamp}.txt"
        
        os.makedirs("qna_responses", exist_ok=True)
        file_path = os.path.join("qna_responses", file_name)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(custom_content)
            return file_path
        except Exception as e:
            print(f"Error saving custom Q&A: {e}")
            return None
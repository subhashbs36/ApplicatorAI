import os
import re
import time
import subprocess
import tempfile
import google.generativeai as genai
from pathlib import Path

class ResumeBuilder:
    """Class for building ATS-friendly resumes using LaTeX templates"""
    
    def __init__(self):
        self.templates_dir = os.path.join(os.getcwd(), "templates")
        self.output_dir = os.path.join(os.getcwd(), "generated_resumes")
        self.temp_resume_content = None
        
        # Ensure directories exist
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
    
    def list_templates(self):
        """List available LaTeX resume templates"""
        templates = [f for f in os.listdir(self.templates_dir) if f.endswith('.tex')]
        return templates if templates else ["default_resume.tex"]
    
    def generate_resume_content(self, resume_content, job_description, sections, keywords, company_name, position_name, template_name):
        """Generate optimized resume content based on the job description"""
        # Store for later use
        self.temp_resume_content = resume_content

        # Read the template
        template_path = os.path.join(self.templates_dir, template_name)
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        # Prepare the prompt for the AI
        prompt = f"""
        You are an expert resume writer. I need you to create an ATS-friendly resume optimized for the following job description:
        
        JOB DESCRIPTION:
        {job_description}
        
        COMPANY: {company_name}
        POSITION: {position_name}
        
        Based on my current resume content below, create a complete LaTeX resume:
        
        MY CURRENT RESUME:
        {resume_content}
        
        I want to include the following sections: {', '.join(sections)}
        
        Keywords to emphasize: {', '.join(keywords) if keywords else 'None specified'}
        
        Here is a LaTeX template to use as a reference. You should modify this template with my information:
        
        {template_content}
        
        using the data from the current resume content and the job description, ensure that the optimized content is:
        - Clear and concise
        - Well-organized and easy to read
        - ATS-friendly by using keywords from the job description
        - Quantify achievements where possible (e.g., "Increased efficiency by 30%")
        - Use action verbs at the beginning of bullet points
        
        Return ONLY the complete LaTeX code for the resume, nothing else.
        """
        
        try:
            # Initialize the Gemini model
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Generate the optimized resume content
            response = model.generate_content(prompt)
            
            # Extract the LaTeX content from the response
            content = response.text
            
            # If the response is in markdown code block format, extract just the LaTeX
            if "```latex" in content:
                content = content.split("```latex")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Store the LaTeX content for later use
            self.temp_latex_content = content
            
            return content
            
        except Exception as e:
            return f"Error generating resume content: {str(e)}"
    
    def generate_resume_pdf(self, resume_preview, template_name, company_name, position_name):
        """Generate a PDF resume using the LaTeX template and optimized content"""
        if not hasattr(self, 'temp_latex_content'):
            return None, "No LaTeX content available. Please generate resume content first."
        
        try:
            # Clean file names for safety
            clean_company = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
            clean_position = re.sub(r'[^\w\s-]', '', position_name).strip().replace(' ', '_')
            timestamp = time.strftime("%Y%m%d%H%M%S")
            output_filename = f"Resume_{clean_company}_{clean_position}_{timestamp}"
            
            # Write the LaTeX content directly to the output directory
            output_tex_path = os.path.join(self.output_dir, f"{output_filename}.tex")
            with open(output_tex_path, 'w', encoding='utf-8') as f:
                f.write(self.temp_latex_content)
            
            # Change to the output directory before running pdflatex
            original_dir = os.getcwd()
            os.chdir(self.output_dir)
            
            try:
                # Run pdflatex in the output directory and capture output
                process = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', f"{output_filename}.tex"],
                    check=False,  # Don't raise exception on non-zero exit
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Check if compilation was successful
                if process.returncode != 0:
                    # Compilation failed, return the error message
                    error_output = process.stdout + process.stderr
                    return None, f"Error during LaTeX compilation: {error_output}"
                
                # Run a second time for references if needed
                subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', f"{output_filename}.tex"],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # The PDF should now be in the output directory
                output_pdf_path = os.path.join(self.output_dir, f"{output_filename}.pdf")
                
                if os.path.exists(output_pdf_path):
                    # Clean up auxiliary files
                    for ext in ['.aux', '.log', '.out']:
                        aux_file = os.path.join(self.output_dir, f"{output_filename}{ext}")
                        if os.path.exists(aux_file):
                            os.remove(aux_file)
                    
                    return output_pdf_path, None  # Return path and no error
                else:
                    # PDF wasn't created despite successful return code
                    return None, "PDF file was not created despite successful compilation."
                
            except Exception as e:
                return None, f"Error during LaTeX compilation: {str(e)}"
                
            finally:
                # Always change back to the original directory
                os.chdir(original_dir)
        
        except Exception as e:
            return None, f"Error generating resume PDF: {str(e)}"

    def fix_latex_errors(self, error_message):
        """Send LaTeX errors to the LLM to get a fixed version of the LaTeX code"""
        if not hasattr(self, 'temp_latex_content'):
            return "No LaTeX content available to fix."
        
        try:
            # Initialize the Gemini model
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Prepare the prompt for the AI
            prompt = f"""
            You are an expert in LaTeX. I have a LaTeX document that is failing to compile with the following error:
            
            ERROR:
            {error_message}
            
            Here is the current LaTeX code:
            
            ```latex
            {self.temp_latex_content}
            ```
            
            Please fix the LaTeX code to resolve the compilation error. Common issues might include:
            1. Special characters that need to be escaped (like &, %, $, #, etc.)
            2. Missing or mismatched braces
            3. Undefined commands or environments
            4. Misplaced alignment characters
            
            Return ONLY the complete fixed LaTeX code, nothing else.
            """
            
            # Generate the fixed LaTeX content
            response = model.generate_content(prompt)
            
            # Extract the LaTeX content from the response
            content = response.text
            
            # If the response is in markdown code block format, extract just the LaTeX
            if "```latex" in content:
                content = content.split("```latex")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Store the fixed LaTeX content
            self.temp_latex_content = content
            
            return content
        
        except Exception as e:
            return f"Error fixing LaTeX content: {str(e)}"
    
    
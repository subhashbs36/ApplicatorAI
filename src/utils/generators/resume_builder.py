import os
import re
import time
import subprocess
import tempfile
import google.generativeai as genai
from pathlib import Path
import gradio as gr

class ResumeBuilder:
    """Class for building ATS-friendly resumes using LaTeX templates"""
    
    def __init__(self):
        # Set up base paths
        self.base_path = Path(__file__).parent.parent.parent.parent
        self.data_path = self.base_path / "src" / "data"
        self.templates_path = self.data_path / "resume_templates"
        self.output_dir = self.data_path / "responses" / "generated_resumes"
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize other attributes
        self.temp_latex_content = None
        
        # Ensure templates directory exists
        self.templates_path.mkdir(parents=True, exist_ok=True)
    
    def list_templates(self):
        """List available LaTeX resume templates"""
        templates = [f.name for f in self.templates_path.iterdir() if f.suffix == '.tex']
        return templates if templates else ["default_resume.tex"]
    
    def generate_resume_content(self, resume_content, job_description, sections, user_suggestion, company_name, position_name, template_name):
        """Generate optimized resume content based on the job description"""
        self.temp_resume_content = resume_content

        # Read the template
        template_path = self.templates_path / template_name
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        # Prepare the prompt for the AI
        prompt = f"""
        You are an expert resume writer specializing in ATS-friendly LaTeX resumes. Create a highly targeted, one-page resume for:
        
        POSITION: {position_name}
        COMPANY: {company_name}
        
        JOB DESCRIPTION:
        {job_description}
        
        Using my current experience:
        {resume_content}
        
        Required sections: {', '.join(sections)}
        Suggestions: {user_suggestion if user_suggestion else 'None specified'}
        
        Follow this LaTeX template structure:
        {template_content}
        
        Key requirements:
        1. Strictly maintain one-page length
        2. Use exact keywords and phrases from the job posting
        3. Include measurable achievements with metrics
        4. Start bullet points with strong action verbs
        5. Maintain proper LaTeX syntax and formatting
        6. Ensure all sections fit within margins
        7. Prioritize relevant experience and skills that match the job description
        8. Quantify achievements whenever possible (%, $, numbers)
        9. Use industry-specific terminology from the job description
        10. If content is too lengthy, prioritize most relevant information and concisely rewrite
        
        IMPORTANT: Analyze the job description for key technical skills, qualifications, and responsibilities. 
        Ensure these are prominently featured in the resume where applicable.
        
        Return ONLY the complete LaTeX code, no explanations.
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

    def add_template(self, template_file):
        """Add a new LaTeX template to the templates directory"""
        if not template_file:
            gr.Warning("No template file provided.")
            return
        
        try:
            # Get the filename from the path
            template_name = Path(template_file).name
            
            # Ensure it's a .tex file
            if not template_name.endswith('.tex'):
                gr.Warning("Invalid file type. Please upload a .tex file.")
                return
            
            # Copy the template to the templates directory
            target_path = self.templates_path / template_name
            
            # Read and write the file to handle different encodings
            with open(template_file, 'r', encoding='utf-8') as source:
                content = source.read()
                
            with open(target_path, 'w', encoding='utf-8') as target:
                target.write(content)
            
            gr.Info(f"Template '{template_name}' added successfully.")
            return
            
        except Exception as e:
            gr.Warning(f"Error adding template: {str(e)}")

    def incorporate_suggestions(self, latex_code, resume_data, sections, suggestions):
        """Incorporate AI suggestions into the LaTeX code"""
        if not latex_code or not suggestions:
            return latex_code
        
        try:
            # Initialize the Gemini model
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Prepare the prompt for the AI
            prompt = f"""
            You are a LaTeX expert. Modify the following LaTeX resume code according to these suggestions:

            SUGGESTIONS:
            {suggestions}

            RESUME DATA:
            {resume_data}

            CURRENT LATEX CODE:
            {latex_code}

            Required sections: {', '.join(sections)}

            Requirements:
            1. Maintain valid LaTeX syntax
            2. Keep the document structure intact
            3. Preserve all necessary packages and commands
            4. Only modify content based on the suggestions
            5. Ensure changes don't break the layout
            6. Keep the content within one page
            7. Take data from RESUME DATA and incorporate it into the LATEX CODE

            Return ONLY the modified LaTeX code, no explanations.
            """
            
            # Generate the modified LaTeX content
            response = model.generate_content(prompt)
            
            # Extract the LaTeX content from the response
            content = response.text
            
            # If the response is in markdown code block format, extract just the LaTeX
            if "```latex" in content:
                content = content.split("```latex")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Store the modified LaTeX content
            self.temp_latex_content = content
            
            return content
            
        except Exception as e:
            print(f"Error incorporating suggestions: {str(e)}")
            return latex_code  # Return original code if there's an error
    
    
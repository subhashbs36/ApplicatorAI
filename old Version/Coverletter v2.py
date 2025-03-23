import os
import gradio as gr
import re
import time
from datetime import date
from dotenv import load_dotenv
import fpdf
import google.generativeai as genai
from pathlib import Path
import PyPDF2
import docx2txt
import hashlib
import json
from functools import lru_cache

# Load environment variables
load_dotenv()

# Configure Gemini API
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise EnvironmentError("Missing GEMINI_API_KEY in environment variables")

genai.configure(api_key=API_KEY)

# Create necessary directories
for dir_name in ["resumes", "cover_letters"]:
    os.makedirs(dir_name, exist_ok=True)

# Constants
MAX_TOKEN_LENGTH = 8000  # Adjust based on model limits
CACHE_EXPIRY = 60 * 60 * 24 * 7  # 7 days in seconds

class ResumeProcessor:
    """Class to handle resume processing operations"""
    
    @staticmethod
    def save_resume(file):
        """Save uploaded resume to the resumes directory"""
        if file is None:
            return None
            
        # Create a safe filename
        original_name = file.name
        safe_name = re.sub(r'[^\w\s.-]', '', original_name)
        file_path = os.path.join("resumes", safe_name)
        
        # Save the file
        with open(file_path, "wb") as f:
            f.write(file.read())
            
        return file_path
    
    @staticmethod
    def extract_text(file_path):
        """Extract text from various file formats"""
        if not file_path or not os.path.exists(file_path):
            return ""
            
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            # Extract text based on file type
            if file_ext == '.pdf':
                return ResumeProcessor._extract_from_pdf(file_path)
            elif file_ext in ['.docx', '.doc']:
                return ResumeProcessor._extract_from_docx(file_path)
            elif file_ext in ['.txt', '.md', '.rtf']:
                return ResumeProcessor._extract_from_text(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
        except Exception as e:
            return f"Error extracting text: {str(e)}"
    
    @staticmethod
    def _extract_from_pdf(file_path):
        """Extract text from PDF files"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    text += pdf_reader.pages[page_num].extract_text() + "\n"
            return text
        except Exception as e:
            raise Exception(f"PDF extraction error: {str(e)}")
    
    @staticmethod
    def _extract_from_docx(file_path):
        """Extract text from Word documents"""
        try:
            return docx2txt.process(file_path)
        except Exception as e:
            raise Exception(f"DOCX extraction error: {str(e)}")
    
    @staticmethod
    def _extract_from_text(file_path):
        """Read plain text files"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Text file reading error: {str(e)}")
    
    @staticmethod
    def list_resumes():
        """List all resume files in the resumes directory"""
        if not os.path.exists("resumes"):
            return []
            
        files = []
        for f in os.listdir("resumes"):
            file_path = os.path.join("resumes", f)
            if os.path.isfile(file_path):
                # Add file info including last modified time
                mod_time = os.path.getmtime(file_path)
                mod_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mod_time))
                size_kb = os.path.getsize(file_path) / 1024
                display_name = f"{f} ({mod_time_str}, {size_kb:.1f} KB)"
                files.append((file_path, display_name))
                
        # Sort by most recent
        files.sort(key=lambda x: os.path.getmtime(x[0]), reverse=True)
        return files


class CoverLetterGenerator:
    """Class to handle cover letter generation operations"""
    
    def __init__(self):
        self.model_name = 'gemini-1.5-pro'  # Updated to use Gemini 1.5 Pro for better results
    
    @staticmethod
    def get_cache_key(resume_content, job_description, company_name, position_name):
        """Generate a unique cache key for the current inputs"""
        data = f"{resume_content}|{job_description}|{company_name}|{position_name}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def check_cache(self, cache_key):
        """Check if there's a cached response for this query"""
        cache_file = os.path.join("cache", f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            # Check if cache is expired
            file_age = time.time() - os.path.getmtime(cache_file)
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
        cache_file = os.path.join("cache", f"{cache_key}.json")
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


class PDFGenerator:
    """Class to handle PDF document generation"""
    @staticmethod
    def create_pdf(cover_letter, output_path):
        """Create a professional-looking PDF document from the cover letter text"""
        pdf = fpdf.FPDF()
        pdf.add_page()
        
        # Reduced margins for better fit (left, top, right)
        pdf.set_margins(15, 15, 15)
        
        # Slightly smaller font size to fit more content on one page
        pdf.set_font("Arial", "", 10)
        
        # Replace smart quotes and other special characters with ASCII equivalents
        cover_letter = cover_letter.replace('\u2018', "'").replace('\u2019', "'")  # Smart single quotes
        cover_letter = cover_letter.replace('\u201c', '"').replace('\u201d', '"')  # Smart double quotes
        cover_letter = cover_letter.replace('\u2013', '-').replace('\u2014', '--')  # En and em dashes
        cover_letter = cover_letter.replace('\u2026', '...')  # Ellipsis
        
        # Add content
        lines = cover_letter.split('\n')  # Split by newline
        in_paragraph = False
        
        for line in lines:
            # Handle empty lines
            if not line.strip():
                pdf.ln(6)  # Smaller line break for compactness
                in_paragraph = False
                continue
            
            # Format different parts of the letter
            if line.strip() == date.today().strftime("%B %d, %Y"):
                # Date
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 8, line, 0, 1)
                pdf.ln(2)
            elif line.startswith("Dear ") or line.startswith("Sincerely,"):
                # Salutation and closing
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 6, line, 0, 1)
                pdf.ln(2)
                in_paragraph = False
            elif len(line) < 30 and not in_paragraph:
                # Likely a header or name
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 6, line, 0, 1)
                in_paragraph = False
            else:
                # Regular paragraph text
                pdf.set_font("Arial", "", 10)
                safe_line = ''.join(char if ord(char) < 128 else '?' for char in line)  # Replace non-ASCII chars
                if in_paragraph:
                    pdf.multi_cell(0, 5, safe_line)  # Reduced line height for compactness
                else:
                    pdf.multi_cell(0, 5, safe_line)
                    in_paragraph = True
        
        # Save the PDF
        try:
            pdf.output(output_path)
            return True
        except Exception as e:
            print(f"Error saving PDF: {str(e)}")
            try:
                simple_pdf = fpdf.FPDF()
                simple_pdf.add_page()
                simple_pdf.set_font("Arial", "", 10)
                ascii_text = cover_letter.encode('ascii', 'replace').decode('ascii')
                simple_pdf.multi_cell(0, 5, ascii_text)
                simple_pdf.output(output_path)
                return True
            except Exception as e_fallback:
                print(f"Fallback PDF save also failed: {str(e_fallback)}")
                return False


class CoverLetterApp:
    """Main application class"""
    def __init__(self):
        self.resume_processor = ResumeProcessor()
        self.cover_letter_generator = CoverLetterGenerator()
        self.pdf_generator = PDFGenerator()
        self.temp_cover_letter = None  # Temporary storage for generated cover letters
    
    def save_cover_letter(self, cover_letter, company_name, position_name):
        """Save the cover letter to a PDF file"""
        if not cover_letter or cover_letter.startswith("Please ") or cover_letter.startswith("Error"):
            return "No valid cover letter to save."
        
        # Clean file names for safety
        clean_company = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
        clean_position = re.sub(r'[^\w\s-]', '', position_name).strip().replace(' ', '_')
        timestamp = time.strftime("%Y%m%d%H%M%S")
        file_name = f"Cover_Letter_{clean_company}_{clean_position}_{timestamp}.pdf"
        
        os.makedirs("cover_letters", exist_ok=True)
        file_path = os.path.join("cover_letters", file_name)
        
        try:
            # Create PDF file
            if self.pdf_generator.create_pdf(cover_letter, file_path):
                return file_path
            
            # Fallback to text file if PDF creation fails
            txt_file_path = file_path.replace(".pdf", ".txt")
            with open(txt_file_path, "w", encoding="utf-8") as f:
                f.write(cover_letter)
            return txt_file_path
        except Exception as e:
            print(f"Error creating file: {e}")
            simple_file_path = os.path.join("cover_letters", f"Cover_Letter_{timestamp}.txt")
            with open(simple_file_path, "w", encoding="utf-8") as f:
                f.write(cover_letter)
            return simple_file_path

    def app_workflow(self, resume_file, selected_resume, job_description, company_name, position_name, progress=gr.Progress()):
        """Main workflow for the application"""
        progress(0, desc="Starting...")
        # Handle the resume file (either uploaded or selected)
        resume_path = None
        if resume_file:
            progress(0.1, desc="Saving uploaded resume...")
            resume_path = self.resume_processor.save_resume(resume_file)
        elif selected_resume:
            resume_path = selected_resume

        if not resume_path:
            return "Please upload or select a resume.", None
        
        # Read resume content
        progress(0.3, desc="Extracting resume content...")
        resume_content = self.resume_processor.extract_text(resume_path)
        if resume_content.startswith("Error"):
            return resume_content, None
        
        # Generate cover letter
        progress(0.5, desc="Generating cover letter...")
        cover_letter = self.cover_letter_generator.generate_cover_letter(
            resume_content, job_description, company_name, position_name
        )
        
        # Store cover letter temporarily instead of saving it right away
        self.temp_cover_letter = cover_letter
        
        progress(1.0, desc="Done!")
        return cover_letter, None  # Return None for file_output to avoid auto-saving
    
    def download_file(self, company_name, position_name):
        """Function to return file for downloading (only triggered when Download PDF button is pressed)"""
        if not self.temp_cover_letter:
            return None
        
        # Save the temporary cover letter to a PDF upon download request
        file_path = self.save_cover_letter(self.temp_cover_letter, company_name, position_name)
        
        if os.path.exists(file_path):
            return file_path
        return None
    
    def refresh_resume_list(self):
        """Refresh the list of available resumes"""
        return gr.update(
            choices=[file_info[0] for file_info in self.resume_processor.list_resumes()],
            value=None
        )

    def build_ui(self):
        """Build the Gradio UI"""
        with gr.Blocks(title="Professional Cover Letter Generator", theme=gr.themes.Soft()) as demo:
            gr.Markdown("# Professional Cover Letter Generator")
            gr.Markdown("Upload your resume, provide job details, and generate a customized cover letter.")
            
            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("## Resume")
                        with gr.Tab("Upload Resume"):
                            resume_file = gr.File(
                                label="Upload Resume (PDF, DOC, DOCX, or TXT)",
                                file_types=[".pdf", ".doc", ".docx", ".txt"],
                                type="binary"
                            )
                        with gr.Tab("Existing Resumes"):
                            resume_dropdown = gr.Dropdown(
                                label="Select Existing Resume", 
                                choices=[file_info[0] for file_info in self.resume_processor.list_resumes()],
                                interactive=True,
                            )
                            refresh_btn = gr.Button("Refresh Resume List", variant="secondary", size="sm")
                    
                    with gr.Group():
                        gr.Markdown("## Job Details")
                        company_name = gr.Textbox(
                            label="Company Name", 
                            placeholder="Enter company name (required)...",
                            info="The company you're applying to"
                        )
                        position_name = gr.Textbox(
                            label="Position Title", 
                            placeholder="Enter position title (required)...",
                            info="The specific role you're applying for"
                        )
                        job_description = gr.Textbox(
                            label="Job Description", 
                            placeholder="Paste the job description here (required)...",
                            lines=10,
                            info="Full job posting text including requirements and responsibilities"
                        )
                        generate_btn = gr.Button("Generate Cover Letter", variant="primary")
                
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("## Generated Cover Letter")
                        cover_letter_output = gr.Textbox(
                            label="Your Cover Letter", 
                            lines=20,
                            show_copy_button=True,
                            info="Your customized cover letter will appear here"
                        )
                        with gr.Row():
                            download_btn = gr.Button("Download Cover Letter as PDF", variant="secondary")
                            download_output = gr.File(label="Download")
            
            # Set up event handlers
            generate_btn.click(
                fn=self.app_workflow,
                inputs=[resume_file, resume_dropdown, job_description, company_name, position_name],
                outputs=[cover_letter_output, download_output]
            )
            
            download_btn.click(
                fn=self.download_file,
                inputs=[company_name, position_name],
                outputs=[download_output]
            )
            
            # Clear resume upload when an existing resume is selected
            resume_dropdown.change(lambda x: None, inputs=[], outputs=[resume_file])
            
            # Refresh resume list
            refresh_btn.click(
                fn=self.refresh_resume_list,
                inputs=[],
                outputs=[resume_dropdown]
            )
            
            # Auto-refresh resume list when a new resume is uploaded
            resume_file.change(
                fn=self.refresh_resume_list,
                inputs=[],
                outputs=[resume_dropdown]
            )
            
            return demo

def main():
    """Main function to run the application"""
    app = CoverLetterApp()
    demo = app.build_ui()
    demo.launch(share=False, debug=True)

if __name__ == "__main__":
    main()
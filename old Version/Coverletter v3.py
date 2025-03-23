import os
import gradio as gr
import re
import time
from datetime import date
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path
import PyPDF2
import docx2txt
import hashlib
import json
from functools import lru_cache
from tools.Crawler import WebCrawler
from tools.pdfGenerator import PDFGenerator
from tools.coverLetterGenerator import *


# Load environment variables
load_dotenv()

# Configure Gemini API
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise EnvironmentError("Missing GEMINI_API_KEY in environment variables")

genai.configure(api_key=API_KEY)

# Create necessary directories
for dir_name in ["resumes", "cover_letters", "cache"]:
    os.makedirs(dir_name, exist_ok=True)


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



class CoverLetterApp:
    """Main application class"""
    def __init__(self):
        self.resume_processor = ResumeProcessor()
        self.cover_letter_generator = CoverLetterGenerator()
        self.pdf_generator = PDFGenerator()
        self.web_crawler = WebCrawler()
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

    def crawl_job_description(self, job_url):
        """Crawl job description from URL"""
        if not job_url:
            return ""
        
        return self.web_crawler.fetch_job_description(job_url)

    def app_workflow(self, resume_file, selected_resume, job_description, job_url, company_name, position_name, progress=gr.Progress()):
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
        progress(0.2, desc="Extracting resume content...")
        resume_content = self.resume_processor.extract_text(resume_path)
        if resume_content.startswith("Error"):
            return resume_content, None
        
        # Get job description (either from text input or by crawling URL)
        final_job_description = job_description
        if job_url and not job_description:
            progress(0.3, desc="Crawling job description from URL...")
            crawled_content = self.crawl_job_description(job_url)
            if crawled_content.startswith("Error"):
                return crawled_content, None
            
            progress(0.4, desc="Processing job description...")
            final_job_description = self.web_crawler.clean_job_description(crawled_content)
        
        if not final_job_description or final_job_description.strip() == "":
            return "Please provide a job description or a valid job posting URL.", None
        
        # Generate cover letter
        progress(0.7, desc="Generating cover letter...")
        cover_letter = self.cover_letter_generator.generate_cover_letter(
            resume_content, final_job_description, company_name, position_name
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
        return gr.Dropdown.update(
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
                        
                        with gr.Tab("Manual Entry"):
                            job_description = gr.Textbox(
                                label="Job Description", 
                                placeholder="Paste the job description here...",
                                lines=10,
                                info="Full job posting text including requirements and responsibilities"
                            )
                        
                        with gr.Tab("Job URL"):
                            job_url = gr.Textbox(
                                label="Job Posting URL", 
                                placeholder="Enter the URL of the job posting (e.g., LinkedIn, Indeed)...",
                                info="We'll automatically extract the job description from this URL"
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
                inputs=[resume_file, resume_dropdown, job_description, job_url, company_name, position_name],
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
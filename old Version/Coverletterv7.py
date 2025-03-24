import os
import gradio as gr
from gradio_pdf import PDF
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
from tools.JobApplicationQnA import JobApplicationQnA
from tools.ColdMailGenerator import ColdMailGenerator
from tools.LinkedInDMGenerator import LinkedInDMGenerator
from tools.pdfProcessing import ResumeProcessor
from tools.ReferralDMGenerator import ReferralDMGenerator
from tools.ResumeBuilder import ResumeBuilder  # Add this import

# Load environment variables
load_dotenv()

# Configure Gemini API
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise EnvironmentError("Missing GEMINI_API_KEY in environment variables")

genai.configure(api_key=API_KEY)

# Create necessary directories
for dir_name in ["resumes", "cover_letters", "cache", "qna_responses", "templates", "generated_resumes"]:
    os.makedirs(dir_name, exist_ok=True)

# Constants
MAX_TOKEN_LENGTH = 8000  # Adjust based on model limits
CACHE_EXPIRY = 60  # 1 minute in seconds




class CoverLetterApp:
    """Main application class"""
    def __init__(self):
        self.resume_processor = ResumeProcessor()
        self.cover_letter_generator = CoverLetterGenerator()
        self.qna_generator = JobApplicationQnA()
        self.pdf_generator = PDFGenerator()
        self.web_crawler = WebCrawler()
        self.cold_mail_generator = ColdMailGenerator()
        self.linkedin_dm_generator = LinkedInDMGenerator()
        self.referral_dm_generator = ReferralDMGenerator()  # Add this line
        self.resume_builder = ResumeBuilder()  # Add the resume builder
        self.temp_cover_letter = None
        self.temp_resume_content = None
        self.temp_job_description = None
        self.questions_answers = []
    
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
        
        # Store resume and job description for QnA feature
        self.temp_resume_content = resume_content
        self.temp_job_description = final_job_description
        
        # Generate cover letter
        progress(0.7, desc="Generating cover letter...")
        cover_letter = self.cover_letter_generator.generate_cover_letter(
            resume_content, final_job_description, company_name, position_name
        )
        
        # Store cover letter temporarily instead of saving it right away
        self.temp_cover_letter = cover_letter
        
        progress(1.0, desc="Done!")
        return cover_letter, None  # Return None for file_output to avoid auto-saving
    
    def generate_qna_answer(self, application_question, word_limit, company_name, position_name):
        """Generate an answer for a job application question"""
        if not self.temp_resume_content or not self.temp_job_description:
            return "Please generate a cover letter first to load your resume and job details."
        
        if not application_question or application_question.strip() == "":
            return "Please enter a question to generate an answer."
        
        # Convert word limit to integer if provided
        word_limit_int = None
        if word_limit and word_limit.strip():
            try:
                word_limit_int = int(word_limit.strip())
            except ValueError:
                return "Word limit must be a number."
        
        # Generate the answer
        answer = self.qna_generator.generate_answer(
            self.temp_resume_content,
            self.temp_job_description,
            application_question,
            company_name,
            position_name,
            word_limit_int
        )
        
        # Store this Q&A pair
        self.questions_answers.append((application_question, answer))
        
        return answer
    
    def clear_qna_history(self):
        """Clear the stored Q&A history"""
        self.questions_answers = []
        return "Q&A history cleared."
    
    def download_qna_file(self, company_name, position_name):
        """Save and download all Q&A responses"""
        if not self.questions_answers:
            return None
        
        file_path = self.qna_generator.save_qna_response(
            self.questions_answers, 
            company_name, 
            position_name
        )
        
        if file_path and os.path.exists(file_path):
            return file_path
        return None
    
    def download_file(self, company_name, position_name, current_cover_letter):
        """Function to return file for downloading (only triggered when Download PDF button is pressed)"""
        if not current_cover_letter:
            return None
        
        # Save the current (possibly edited) cover letter to a PDF upon download request
        file_path = self.save_cover_letter(current_cover_letter, company_name, position_name)
        
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
        # Create a custom theme with better colors and fonts
        custom_theme = gr.themes.Soft(
            primary_hue="purple",
            secondary_hue="purple", 
            neutral_hue="zinc",
            font=[gr.themes.GoogleFont("Poppins"), gr.themes.GoogleFont("Roboto"), "system-ui", "sans-serif"],
            font_mono=[gr.themes.GoogleFont("Fira Code"), "ui-monospace", "Consolas", "monospace"],
        )
        
        with gr.Blocks(title="Professional Job Application Assistant", theme=custom_theme) as demo:
            # Create a stylish header with custom CSS
            gr.Markdown(
                """
                <div style="text-align: center; padding: 20px; background: linear-gradient(90deg, #6366f1, #8b5cf6); border-radius: 10px; margin-bottom: 20px;">
                    <h1 style="color: white; font-size: 2.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); margin: 0;">
                        ✨ Professional Job Application Assistant ✨
                    </h1>
                    <p style="color: #f3f4f6; font-size: 1.2em; margin-top: 10px;">
                        Your AI-powered companion for crafting perfect job applications
                    </p>
                    <p style="color: #f3f4f6; font-size: 1.2em; margin-top: 5px;">
                        📝 <strong>Getting Started:</strong> Upload your resume, provide job details, and let our AI help you generate 
                    </p>
                </div>
                """
            )
            
            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("## Resume")
                        with gr.Tab("Existing Resumes"):
                            resume_dropdown = gr.Dropdown(
                                label="Select Existing Resume", 
                                choices=[file_info[0] for file_info in self.resume_processor.list_resumes()],
                                interactive=True,
                            )
                            refresh_btn = gr.Button("Refresh Resume List", variant="secondary", size="sm")

                        with gr.Tab("Upload Resume"):
                            resume_file = gr.File(
                                label="Upload Resume (PDF, DOC, DOCX, or TXT)",
                                file_types=[".pdf", ".doc", ".docx", ".txt"],
                                type="filepath"  # Changed from "binary" to "filepath"
                            )
                    
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
                       
                        with gr.Tab("Job URL"):
                            job_url = gr.Textbox(
                                label="Job Posting URL", 
                                placeholder="Enter the URL of the job posting (e.g., LinkedIn, Indeed)...",
                                info="We'll automatically extract the job description from this URL"
                            )
                                                    
                        with gr.Tab("Manual Entry"):
                            job_description = gr.Textbox(
                                label="Job Description", 
                                placeholder="Paste the job description here...",
                                lines=10,
                                info="Full job posting text including requirements and responsibilities"
                            )
                            
                        with gr.Row():
                            with gr.Column(scale=1):
                                generate_btn = gr.Button("Generate Cover Letter", variant="primary")
                            with gr.Column(scale=1):
                                reset_btn = gr.Button("Reset Form", variant="secondary")
                
                with gr.Column(scale=1):
                    with gr.Tabs() as tabs:
                        with gr.TabItem("Cover Letter"):
                            with gr.Group():
                                gr.Markdown("## Generated Cover Letter")
                                cover_letter_output = gr.Textbox(
                                    label="Your Cover Letter", 
                                    lines=20,
                                    show_copy_button=True,
                                    info="Your customized cover letter will appear here. Feel free to edit before downloading.",
                                    interactive=True  # Make the textbox editable
                                )
                                download_btn = gr.Button("Download PDF", variant="secondary")
                                download_output = gr.File()
                        
                        with gr.TabItem("Application Q&A"):
                            with gr.Group():
                                gr.Markdown("## Job Application Questions")
                                gr.Markdown("Generate personalized answers to job application questions based on your resume and the job description.")
                                
                                with gr.Tab("Single Question"):
                                    application_question = gr.Textbox(
                                        label="Application Question", 
                                        placeholder="Enter a job application question...",
                                        lines=2,
                                        info="Enter a question from the job application"
                                    )
                                    
                                    word_limit = gr.Textbox(
                                        label="Word Limit (Optional)", 
                                        placeholder="Enter word limit if specified (e.g., 200)...",
                                        info="Optional: Specify the word limit for your answer if required"
                                    )
                                    
                                    answer_btn = gr.Button("Generate Answer", variant="primary")
                                    
                                    answer_output = gr.Textbox(
                                        label="Your Answer", 
                                        lines=10,
                                        show_copy_button=True,
                                        info="Your personalized answer will appear here. Feel free to edit before saving.",
                                        interactive=True  # Make the textbox editable
                                    )
                                
                                with gr.Tab("Batch Questions"):
                                    batch_questions = gr.Textbox(
                                        label="Multiple Questions", 
                                        placeholder="Enter one question per line...",
                                        lines=10,
                                        info="Enter multiple job application questions, one per line"
                                    )
                                    
                                    batch_word_limit = gr.Textbox(
                                        label="Word Limit (Optional)", 
                                        placeholder="Enter word limit if specified (e.g., 200)...",
                                        info="Optional: Apply this word limit to all answers"
                                    )
                                    
                                    # Removed redundant company and position fields
                                    
                                    batch_generate_btn = gr.Button("Generate All Answers", variant="primary")
                                    
                                    batch_output = gr.Textbox(
                                        label="Generated Answers", 
                                        lines=15,
                                        show_copy_button=True,
                                        info="All your personalized answers will appear here. Feel free to edit before downloading.",
                                        interactive=True  # Make the textbox editable
                                    )
                                    
                                    batch_download_btn = gr.Button("Download Batch Answers", variant="secondary")
                                    batch_download_output = gr.File(label="Download Batch Q&A")
                                
                                # Display Q&A history
                                gr.Markdown("### Your Q&A History")
                                qna_history_output = gr.Markdown("No questions answered yet.")
                                
                                with gr.Row():
                                    with gr.Column(scale=1):
                                        clear_qa_btn = gr.Button("Clear Q&A History", variant="secondary")
                                    with gr.Column(scale=1):
                                        download_qa_btn = gr.Button("Download All Q&A Responses", variant="secondary")
                                        download_qa_output = gr.File(label="Files")
                                    
                        # Moving Outreach Messages as a tab inside the existing tabs structure
                        with gr.TabItem("Outreach Messages"):
                            with gr.Group():
                                gr.Markdown("## Professional Outreach Messages")
                                gr.Markdown("Generate personalized cold emails and LinkedIn messages to hiring managers based on your resume and the job description.")
                                
                                # Move hr_name inside the tabs that need it
                                with gr.Tab("Cold Email"):
                                    hr_name_email = gr.Textbox(
                                        label="Hiring Manager/Recruiter Name (Optional)", 
                                        placeholder="Enter the name of the hiring manager or recruiter if known...",
                                        info="Leave blank to use a generic greeting"
                                    )
                                    
                                    cold_mail_btn = gr.Button("Generate Cold Email", variant="primary")
                                    
                                    cold_mail_output = gr.Textbox(
                                        label="Your Cold Email", 
                                        lines=12,
                                        show_copy_button=True,
                                        info="Your personalized cold email will appear here. Feel free to edit before downloading.",
                                        interactive=True  # Make the textbox editable
                                    )
                                    
                                    download_cold_mail_btn = gr.Button("Download Cold Email", variant="secondary")
                                    download_cold_mail_output = gr.File(label="Download Email")
                                
                                with gr.Tab("LinkedIn DM"):
                                    hr_name_linkedin = gr.Textbox(
                                        label="Hiring Manager/Recruiter Name (Optional)", 
                                        placeholder="Enter the name of the hiring manager or recruiter if known...",
                                        info="Leave blank to use a generic greeting"
                                    )
                                    
                                    linkedin_dm_btn = gr.Button("Generate LinkedIn Message", variant="primary")
                                    
                                    linkedin_dm_output = gr.Textbox(
                                        label="Your LinkedIn Message", 
                                        lines=8,
                                        show_copy_button=True,
                                        info="Your personalized LinkedIn message will appear here. Feel free to edit before downloading.",
                                        interactive=True  # Make the textbox editable
                                    )
                                    
                                    download_linkedin_dm_btn = gr.Button("Download LinkedIn Message", variant="secondary")
                                    download_linkedin_dm_output = gr.File(label="Download Message")
                                
                                # Add new Referrals DM tab without the HR name field
                                with gr.Tab("Referrals DM"):
                                    referral_name = gr.Textbox(
                                        label="Connection Name", 
                                        placeholder="Enter the name of your connection who works at the target company...",
                                        info="The person you're asking for a referral from"
                                    )
                                    
                                    referral_btn = gr.Button("Generate Referral Request", variant="primary")
                                    
                                    referral_output = gr.Textbox(
                                        label="Your Referral Request", 
                                        lines=8,
                                        show_copy_button=True,
                                        info="Your personalized referral request message will appear here. Feel free to edit before downloading.",
                                        interactive=True  # Make the textbox editable
                                    )
                                    
                                    download_referral_btn = gr.Button("Download Referral Message", variant="secondary")
                                    download_referral_output = gr.File(label="Download Message")

                        # Add new Resume Builder tab
                        with gr.TabItem("Resume Builder"):
                            with gr.Group():
                                gr.Markdown("## ATS-Friendly Resume Builder")
                                gr.Markdown("Generate a tailored resume optimized for the job description using LaTeX templates.")
                                
                                resume_template = gr.Dropdown(
                                    label="Select Resume Template", 
                                    choices=self.resume_builder.list_templates(),
                                    interactive=True,
                                    info="Choose a LaTeX template for your resume"
                                )
                                
                                refresh_templates_btn = gr.Button("Refresh Templates", variant="secondary", size="sm")
                                
                                resume_sections = gr.CheckboxGroup(
                                    label="Resume Sections to Include",
                                    choices=["Education", "Experience", "Skills", "Projects", "Certifications", "Publications", "Awards"],
                                    value=["Education", "Experience", "Skills"],
                                    info="Select which sections to include in your resume"
                                )
                                
                                keywords_to_highlight = gr.Textbox(
                                    label="Keywords to Highlight (Optional)", 
                                    placeholder="Enter keywords from the job description to emphasize in your resume...",
                                    info="Separate keywords with commas"
                                )
                                
                                build_resume_btn = gr.Button("Build Optimized Resume", variant="primary")
                                
                                with gr.Row():
                                    with gr.Column(scale=1):
                                        resume_latex_preview = gr.Textbox(
                                            label="LaTeX Code", 
                                            lines=20,
                                            show_copy_button=True,
                                            info="LaTeX code for your resume",
                                            interactive=True
                                        )
                                        latex_console = gr.Textbox(
                                            label="LaTeX Console output", 
                                            lines=3,
                                            show_copy_button=False,
                                            # info="LaTeX console output",
                                            interactive=False
                                        )                                    

                                    with gr.Column():                                
                                        pdf_preview = PDF(
                                            label="PDF Preview",
                                            visible=True,
                                            interactive=True
                                        )
                                
                                with gr.Row():
                                    with gr.Column(scale=1):
                                        fix_latex_pdf_btn = gr.Button("Auto Fix Error", variant="primary")
                                    with gr.Column(scale=1):
                                        recompile_pdf_btn = gr.Button("ReCompile", variant="primary")
                                    
                                    with gr.Column(scale=1):
                                        download_resume_btn = gr.Button("Download Resume PDF", variant="primary")
                                        download_resume_output = gr.File(label="Download Resume")

                # Set up event handlers
                generate_btn.click(
                    fn=self.app_workflow,
                    inputs=[
                        resume_file, 
                        resume_dropdown, 
                        job_description,
                        job_url,
                        company_name,
                        position_name
                    ],
                    outputs=[cover_letter_output, download_output]
                )
                
                # Update event handlers to pass current content
                download_btn.click(
                    fn=self.download_file,
                    inputs=[company_name, position_name, cover_letter_output],
                    outputs=download_output
                )
                
                refresh_btn.click(
                    fn=self.refresh_resume_list,
                    inputs=[],
                    outputs=resume_dropdown
                )
                
                # Add reset button handler
                reset_btn.click(
                    fn=self.reset_form,
                    inputs=[],
                    outputs=[
                        job_description, job_url, company_name, position_name, cover_letter_output,
                        application_question, word_limit, answer_output, batch_questions, batch_word_limit,
                        batch_output, hr_name_email, cold_mail_output,
                        hr_name_linkedin, linkedin_dm_output, referral_name, referral_output, qna_history_output
                    ]
                )
                
                # Q&A tab functionality
                answer_btn.click(
                    fn=self.generate_qna_answer,
                    inputs=[application_question, word_limit, company_name, position_name],
                    outputs=answer_output
                )
                
                clear_qa_btn.click(
                    fn=self.clear_qna_history,
                    inputs=[],
                    outputs=qna_history_output
                )
                
                download_qa_btn.click(
                    fn=self.download_qna_file,
                    inputs=[company_name, position_name, qna_history_output],
                    outputs=download_qa_output
                )
                
                # Update Q&A history whenever a new answer is generated
                answer_btn.click(
                    fn=self.update_qna_history,
                    inputs=[],
                    outputs=qna_history_output
                )
                
                # Batch Q&A tab functionality
                batch_generate_btn.click(
                    fn=self.generate_batch_answers,
                    inputs=[batch_questions, batch_word_limit, company_name, position_name],
                    outputs=batch_output
                )
                
                batch_download_btn.click(
                    fn=self.download_batch_file,
                    inputs=[company_name, position_name, batch_output],
                    outputs=batch_download_output
                )
                
                # New tab for Cold Mail and LinkedIn DM
                cold_mail_btn.click(
                    fn=self.generate_cold_mail,
                    inputs=[hr_name_email, company_name, position_name],
                    outputs=cold_mail_output
                )
                
                download_cold_mail_btn.click(
                    fn=self.download_cold_mail,
                    inputs=[company_name, position_name, cold_mail_output],
                    outputs=download_cold_mail_output
                )
                
                linkedin_dm_btn.click(
                    fn=self.generate_linkedin_dm,
                    inputs=[hr_name_linkedin, company_name, position_name],
                    outputs=linkedin_dm_output
                )
                
                download_linkedin_dm_btn.click(
                    fn=self.download_linkedin_dm,
                    inputs=[company_name, position_name, linkedin_dm_output],
                    outputs=download_linkedin_dm_output
                )

                download_referral_btn.click(
                    fn=self.download_referral_dm,
                    inputs=[company_name, position_name, referral_output],
                    outputs=download_referral_output
                )

                # Add Resume Builder event handlers
                refresh_templates_btn.click(
                    fn=self.resume_builder.list_templates,
                    inputs=[],
                    outputs=resume_template
                )
                
                # Update the build_resume_btn click handler to output to both preview components
                build_resume_btn.click(
                    fn=self.build_optimized_resume,
                    inputs=[
                        resume_template,
                        resume_sections,
                        keywords_to_highlight,
                        company_name,
                        position_name
                    ],
                    outputs=[resume_latex_preview, latex_console, pdf_preview]
                )
                
                # Add a handler for the recompile_pdf_btn
                recompile_pdf_btn.click(
                    fn=self.latex_compiler,
                    inputs=[resume_latex_preview],
                    outputs=[pdf_preview, latex_console]  # Update both outputs
                )

                fix_latex_pdf_btn.click(
                    fn=self.latex_code_fixer,
                    inputs=[resume_latex_preview],
                    outputs=[resume_latex_preview, latex_console, pdf_preview]
                )

                # Update the download_resume_btn click handler
                download_resume_btn.click(
                    fn=self.download_resume,
                    inputs=[company_name, position_name, resume_latex_preview, resume_template],
                    outputs=download_resume_output
                )
                
                # Add referral button handler that was missing
                referral_btn.click(
                    fn=self.generate_referral_dm,
                    inputs=[referral_name, company_name, position_name],
                    outputs=referral_output
                )

                return demo


    def update_qna_history(self):
        """Update the Q&A history display"""
        if not self.questions_answers:
            return "No questions answered yet."
        
        # Format the Q&A history as markdown
        history = ""
        for i, (question, answer) in enumerate(self.questions_answers):
            history += f"**Question {i+1}:** {question}\n\n"
            history += f"**Answer {i+1}:** {answer}\n\n"
            history += "---\n\n"
        
        return history
        
    def generate_cold_mail(self, hr_name, company_name, position_name):
        """Generate a cold mail to a hiring manager"""
        if not self.temp_resume_content or not self.temp_job_description:
            return "Please generate a cover letter first to load your resume and job details."
        
        if not company_name or not position_name:
            return "Please provide both company name and position title."
        
        return self.cold_mail_generator.generate_cold_mail(
            self.temp_resume_content,
            self.temp_job_description,
            hr_name,
            company_name,
            position_name
        )
    
    def generate_linkedin_dm(self, hr_name, company_name, position_name):
        """Generate a LinkedIn DM to a hiring manager"""
        if not self.temp_resume_content or not self.temp_job_description:
            return "Please generate a cover letter first to load your resume and job details."
        
        if not company_name or not position_name:
            return "Please provide both company name and position title."
        
        return self.linkedin_dm_generator.generate_linkedin_dm(
            self.temp_resume_content,
            self.temp_job_description,
            hr_name,
            company_name,
            position_name
        )
    
    def download_cold_mail(self, company_name, position_name):
        """Save and download the cold mail as a text file"""
        cold_mail = self.cold_mail_generator.temp_cold_mail
        if not cold_mail:
            return None
        
        return self.cold_mail_generator.save_cold_mail(cold_mail, company_name, position_name)
    
    def download_linkedin_dm(self, company_name, position_name):
        """Save and download the LinkedIn DM as a text file"""
        linkedin_dm = self.linkedin_dm_generator.temp_linkedin_dm
        if not linkedin_dm:
            return None
        
        return self.linkedin_dm_generator.save_linkedin_dm(linkedin_dm, company_name, position_name)

    def generate_referral_dm(self, referral_name, company_name, position_name):
        """Generate a LinkedIn DM to request a referral"""
        if not self.temp_resume_content or not self.temp_job_description:
            return "Please generate a cover letter first to load your resume and job details."
        
        if not company_name or not position_name:
            return "Please provide both company name and position title."
            
        if not referral_name:
            return "Please provide the name of your connection to personalize the message."
        
        return self.referral_dm_generator.generate_referral_dm(
            self.temp_resume_content,
            self.temp_job_description,
            referral_name,
            company_name,
            position_name
        )
    
    def download_referral_dm(self, company_name, position_name):
        """Save and download the referral DM as a text file"""
        referral_dm = self.referral_dm_generator.temp_referral_dm
        if not referral_dm:
            return None
        
        return self.referral_dm_generator.save_referral_dm(referral_dm, company_name, position_name)

    def generate_batch_answers(self, batch_questions, word_limit, company_name, position_name):
        """Generate answers for multiple questions at once"""
        if not self.temp_resume_content or not self.temp_job_description:
            return "Please generate a cover letter first to load your resume and job details."
        
        if not batch_questions or batch_questions.strip() == "":
            return "Please enter at least one question to generate answers."
        
        # Parse the questions (one per line)
        questions = [q.strip() for q in batch_questions.split('\n') if q.strip()]
        
        if not questions:
            return "Please enter at least one valid question."
        
        # Convert word limit to integer if provided
        word_limit_int = None
        if word_limit and word_limit.strip():
            try:
                word_limit_int = int(word_limit.strip())
            except ValueError:
                return "Word limit must be a number."
        
        # Generate answers for all questions
        results = []
        for question in questions:
            answer = self.qna_generator.generate_answer(
                self.temp_resume_content,
                self.temp_job_description,
                question,
                company_name,
                position_name,
                word_limit_int
            )
            
            # Add to Q&A history
            self.questions_answers.append((question, answer))
            
            # Format for display
            results.append(f"Q: {question}\n\nA: {answer}\n\n---\n")
        
        # Combine all results
        return "\n".join(results)

    def download_batch_file(self, company_name, position_name):
        """Save and download batch Q&A responses"""
        # Use the existing QnA save functionality
        return self.download_qna_file(company_name, position_name)

    def build_optimized_resume(self, template_name, sections, keywords, company_name, position_name):
        """Build an optimized resume based on the selected template and job description"""
        if not self.temp_resume_content or not self.temp_job_description:
            return "Please generate a cover letter first to load your resume and job details.", "Please generate a cover letter first to load your resume and job details."
        
        if not template_name:
            return "Please select a resume template.", "Please select a resume template."
        
        if not company_name or not position_name:
            return "Please provide both company name and position title.", "Please provide both company name and position title."
        
        # Convert keywords string to list
        keyword_list = [k.strip() for k in keywords.split(',')] if keywords else []
        
        # Generate optimized resume content
        resume_content = self.resume_builder.generate_resume_content(
            self.temp_resume_content,
            self.temp_job_description,
            sections,
            keyword_list,
            company_name,
            position_name,
            template_name
        )
        
        # Check if the resume_content is a string (error message)
        if isinstance(resume_content, str) and (resume_content.startswith("Error") or resume_content.startswith("Please")):
            return resume_content, resume_content
        
        pdf_path, error = self.resume_builder.generate_resume_pdf(
            resume_content,
            template_name,
            company_name,
            position_name
        )
        
        # Return LaTeX content and either success message or error message
        if error or pdf_path is None:
            fixed_latex = self.resume_builder.fix_latex_errors(error)
            
            # Try to compile again with the fixed LaTeX
            pdf_path, error = self.resume_builder.generate_resume_pdf(
                fixed_latex,  # Use the fixed content
                template_name,
                company_name,
                position_name
            )

            if error or pdf_path is None:
                gr.Warning(f"Failed to compile LaTeX after attempting fixes")
                return resume_content, f"LaTeX Compilation Error:\n\nPlease Run Fix-Resume", None
            else:
                return resume_content, f"✅ LaTeX compilation successful!", pdf_path
        else:
            return resume_content, f"✅ LaTeX compilation successful!2", pdf_path
        

    def download_resume(self, company_name, position_name, resume_content, template_name):
        """Generate and download the resume PDF"""
        if not resume_content or resume_content.startswith("Please ") or resume_content.startswith("Error"):
            return None
        
        # Generate the resume PDF using the template
        file_path, error = self.resume_builder.generate_resume_pdf(
            resume_content,
            template_name,
            company_name,
            position_name
        )
        
        # If there was an error during compilation, try to fix it
        if error and not file_path:
            # Try to fix the LaTeX errors
            fixed_latex = self.resume_builder.fix_latex_errors(error)
            
            # Try to compile again with the fixed LaTeX
            file_path, error = self.resume_builder.generate_resume_pdf(
                fixed_latex,  # Use the fixed content
                template_name,
                company_name,
                position_name
            )
            
            # If still failing, return the error
            if error and not file_path:
                gr.Warning(f"Failed to compile LaTeX after attempting fixes: {error}")
                return None
        
        if file_path and os.path.exists(file_path):
            return file_path
        return None

    def latex_compiler(self, latex_code):
        """Fix LaTeX errors in the provided code"""
        if not latex_code:
            return None, "Please generate resume content first."
        
        # Store the LaTeX code in the resume builder
        self.resume_builder.temp_latex_content = latex_code

        # Try to compile and see if there are errors
        file_path, error = self.resume_builder.generate_resume_pdf(
            latex_code,
            "temp_template.tex",
            "temp_company",
            "temp_position"
        )

        if error or file_path is None:
            gr.Warning(f"Failed to compile LaTeX recheck the code or rebuild the resume")
            return None, f"LaTeX Compilation Error:\n\nPlease Re-run Build"
        
        if file_path and os.path.exists(file_path):
            return file_path, f"✅ LaTeX compilation successful! Click 'Download Resume PDF' to save the file."
        return None, "Failed to generate PDF"

    def latex_code_fixer(self, latex_code):
        """Fix LaTeX errors in the provided code"""
        if not latex_code:
            return None, "Please generate resume content first.", "<p>No content to fix</p>"

        # Store the LaTeX code in the resume builder
        self.resume_builder.temp_latex_content = latex_code
        # Try to compile and see if there are errors
        file_path, error = self.resume_builder.generate_resume_pdf(
            latex_code,
            "temp_template.tex",
            "temp_company",
            "temp_position"
        )

        if error or file_path is None:
            # Try to fix the LaTeX errors
            fixed_latex = self.resume_builder.fix_latex_errors(error)
            # Try to compile again with the fixed LaTeX
            file_path, error = self.resume_builder.generate_resume_pdf(
                fixed_latex,  # Use the fixed content
                "temp_template.tex",
                "temp_company",
                "temp_position" 
            )

        if error or file_path is None:
            fixed_latex = self.resume_builder.fix_latex_errors(error)
            file_path, error = self.resume_builder.generate_resume_pdf(
                fixed_latex,
                "temp_template.tex",
                "temp_company",
                "temp_position" 
            )

            if error or file_path is None:
                gr.Warning(f"Failed to compile LaTeX after attempting fixes")
                return latex_code, f"❌ LaTeX Compilation Error:\n{error}", None

            return fixed_latex, f"✅ Fixed LaTeX errors and compiled successfully!", file_path

        return latex_code, "✅ No errors found in LaTeX code!", file_path

    def reset_form(self):
        """Reset all form fields and temporary data except resumes"""
        # Clear temporary data
        self.temp_cover_letter = None
        self.temp_resume_content = None
        self.temp_job_description = None
        self.questions_answers = []
        
        # Return empty values for all form fields
        return (
            None,  # job_description
            None,  # job_url
            None,  # company_name
            None,  # position_name
            "",    # cover_letter_output
            None,  # application_question
            None,  # word_limit
            "",    # answer_output
            None,  # batch_questions
            None,  # batch_word_limit
            "",    # batch_output
            None,  # hr_name_email
            "",    # cold_mail_output
            None,  # hr_name_linkedin
            "",    # linkedin_dm_output
            None,  # referral_name
            "",    # referral_output
            "No questions answered yet.",  # qna_history_output
            None,  # resume_template
            ["Education", "Experience", "Skills"],  # resume_sections
            None,  # keywords_to_highlight
            "",    # latex_console
        )

def main():
    """Main function to run the application"""
    app = CoverLetterApp()
    demo = app.build_ui()
    demo.launch(share=False, debug=True)

if __name__ == "__main__":
    main()
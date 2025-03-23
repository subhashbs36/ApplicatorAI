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
from tools.JobApplicationQnA import JobApplicationQnA
from pdfProcessing import ResumeProcessor

# Load environment variables
load_dotenv()

# Configure Gemini API
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise EnvironmentError("Missing GEMINI_API_KEY in environment variables")

genai.configure(api_key=API_KEY)

# Create necessary directories
for dir_name in ["resumes", "cover_letters", "cache", "qna_responses"]:
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
        self.temp_cover_letter = None  # Temporary storage for generated cover letters
        self.temp_resume_content = None  # Store resume content for reuse
        self.temp_job_description = None  # Store job description for reuse
        self.questions_answers = []  # Store Q&A pairs
    
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
        # Create a custom theme with better colors and fonts
        custom_theme = gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="indigo",
            neutral_hue="slate",
            font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
            font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "Consolas", "monospace"],
        )
        
        with gr.Blocks(title="Professional Job Application Assistant", theme=custom_theme) as demo:
            gr.Markdown("# Professional Job Application Assistant")
            gr.Markdown("Upload your resume, provide job details, and generate customized application materials.")
            
            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("## Resume")
                        with gr.Tab("Upload Resume"):
                            resume_file = gr.File(
                                label="Upload Resume (PDF, DOC, DOCX, or TXT)",
                                file_types=[".pdf", ".doc", ".docx", ".txt"],
                                type="filepath"  # Changed from "binary" to "filepath"
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
                    with gr.Tabs() as tabs:
                        with gr.TabItem("Cover Letter"):
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
                        
                        with gr.TabItem("Application Q&A"):
                            with gr.Group():
                                gr.Markdown("## Job Application Questions")
                                gr.Markdown("Generate personalized answers to job application questions based on your resume and the job description.")
                                
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
                                    info="Your personalized answer will appear here"
                                )
                                
                                # Display Q&A history
                                gr.Markdown("### Your Q&A History")
                                qna_history_output = gr.Markdown("No questions answered yet.")
                                
                                with gr.Row():
                                    clear_qa_btn = gr.Button("Clear Q&A History", variant="secondary")
                                    download_qa_btn = gr.Button("Download All Q&A Responses", variant="secondary")
                                    download_qa_output = gr.File(label="Download Q&A")
                                    
                        with gr.TabItem("Batch Q&A"):
                            with gr.Group():
                                gr.Markdown("## Batch Question Processing")
                                gr.Markdown("Enter multiple questions at once and generate answers for all of them.")
                                
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
                                
                                # Add company and position fields in this tab as well
                                batch_company_name = gr.Textbox(
                                    label="Company Name", 
                                    placeholder="Enter company name (required)...",
                                    info="The company you're applying to"
                                )
                                
                                batch_position_name = gr.Textbox(
                                    label="Position Title", 
                                    placeholder="Enter position title (required)...",
                                    info="The specific role you're applying for"
                                )
                                
                                batch_generate_btn = gr.Button("Generate All Answers", variant="primary")
                                
                                batch_output = gr.Textbox(
                                    label="Generated Answers", 
                                    lines=15,
                                    show_copy_button=True,
                                    info="All your personalized answers will appear here"
                                )
                                
                                with gr.Row():
                                    batch_download_btn = gr.Button("Download Batch Answers", variant="secondary")
                                    batch_download_output = gr.File(label="Download Batch Q&A")
            
                # Set up event handlers - fix indentation to be at this level
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
                ).then(
                    fn=lambda: gr.Tabs.update(selected="Cover Letter"),
                    inputs=None,
                    outputs=tabs
                )
                download_btn.click(
                    fn=self.download_file,
                    inputs=[company_name, position_name],
                    outputs=download_output
                )
                
                refresh_btn.click(
                    fn=self.refresh_resume_list,
                    inputs=[],
                    outputs=resume_dropdown
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
                    inputs=[company_name, position_name],
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
                    inputs=[batch_questions, batch_word_limit, batch_company_name, batch_position_name],
                    outputs=batch_output
                )
                
                batch_download_btn.click(
                    fn=self.download_batch_file,
                    inputs=[batch_company_name, batch_position_name],
                    outputs=batch_download_output
                )
                
                return demo
        

    def update_qna_history(self):
        """Update the Q&A history display"""
        if not self.questions_answers:
            return "No questions answered yet."
        
        # Format the Q&A history as markdown
        history = "### Your Q&A History\n\n"
        for i, (question, answer) in enumerate(self.questions_answers):
            history += f"**Question {i+1}:** {question}\n\n"
            history += f"**Answer {i+1}:** {answer}\n\n"
            history += "---\n\n"
        
        return history

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


def main():
    """Main function to run the application"""
    app = CoverLetterApp()
    demo = app.build_ui()
    demo.launch(share=False, debug=True)

if __name__ == "__main__":
    main()
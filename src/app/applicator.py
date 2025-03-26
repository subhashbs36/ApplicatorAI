import os
import gradio as gr
import re
import time
from pathlib import Path
from ..utils.generators.cover_letter_generator import CoverLetterGenerator
from ..utils.generators.job_application_qna import JobApplicationQnA
from ..utils.generators.ai_mail_generator import AiMailGenerator  # Add this import
from ..utils.generators.cover_letter_to_pdf import PDFGenerator
from ..utils.generators.cold_mail_generator import ColdMailGenerator
from ..utils.generators.linkedin_dm_generator import LinkedInDMGenerator
from ..utils.generators.referral_dm_generator import ReferralDMGenerator
from ..utils.generators.resume_builder import ResumeBuilder
from ..utils.generators.resume_processor import ResumeProcessor
from ..utils.web_crawler import WebCrawler
from ..ui.components import create_header, create_resume_section, create_job_details_section, create_features_section
from ..ui.event_handlers import setup_event_handlers
from src.utils.job_extractor import JobDetailsExtractor

class Applicator:
    """Main application class"""
    def __init__(self):
        # Set up base paths
        self.base_path = Path(__file__).parent.parent.parent
        self.data_path = self.base_path / "src" / "data"
        self.responses_path = self.data_path / "responses"
        
        # Set up response type paths
        self.cache_path = self.responses_path / "cache"
        self.cold_mails_path = self.responses_path / "cold_mails"
        self.cover_letters_path = self.responses_path / "cover_letters"
        self.generated_resumes_path = self.responses_path / "generated_resumes"
        self.generated_pdfs_path = self.responses_path / "generated_pdfs"
        self.linkedin_dms_path = self.responses_path / "linkedin_dms"
        self.qna_responses_path = self.responses_path / "qna_responses"
        self.ai_mail_generator = AiMailGenerator()  # Add this line
        self.ai_mails_path = self.responses_path / "ai_mails"  # Add this line
        
        # Update directory creation
        for path in [self.cache_path, self.cold_mails_path, self.cover_letters_path,
                    self.generated_resumes_path, self.generated_pdfs_path,
                    self.linkedin_dms_path, self.qna_responses_path, self.ai_mails_path]:  # Add ai_mails_path
            path.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.resume_processor = ResumeProcessor()
        self.cover_letter_generator = CoverLetterGenerator()
        self.qna_generator = JobApplicationQnA()
        self.pdf_generator = PDFGenerator()
        self.web_crawler = WebCrawler()
        self.cold_mail_generator = ColdMailGenerator()
        self.linkedin_dm_generator = LinkedInDMGenerator()
        self.referral_dm_generator = ReferralDMGenerator()  # Add this line
        self.resume_builder = ResumeBuilder()  # Add the resume builder
        self.job_extractor = JobDetailsExtractor()
        self.temp_cover_letter = None
        self.temp_resume_content = None
        self.temp_job_description = None
        self.questions_answers = []
        self.company_name = None
        self.position_name = None
    
    def save_cover_letter(self, cover_letter, company_name, position_name):
        """Save the cover letter to a PDF file"""
        if not cover_letter or cover_letter.startswith("Please ") or cover_letter.startswith("Error"):
            return "No valid cover letter to save."
        
        # Clean file names for safety
        clean_company = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
        clean_position = re.sub(r'[^\w\s-]', '', position_name).strip().replace(' ', '_')
        timestamp = time.strftime("%Y%m%d%H%M%S")
        file_name = f"Cover_Letter_{clean_company}_{clean_position}_{timestamp}.pdf"
        
        file_path = self.cover_letters_path / file_name
        
        try:
            # Create PDF file
            if self.pdf_generator.create_pdf(cover_letter, str(file_path)):
                return str(file_path)
            
            # Fallback to text file if PDF creation fails
            txt_file_path = file_path.with_suffix('.txt')
            with open(txt_file_path, "w", encoding="utf-8") as f:
                f.write(cover_letter)
            return str(txt_file_path)
        except Exception as e:
            print(f"Error creating file: {e}")
            simple_file_path = self.cover_letters_path / f"Cover_Letter_{timestamp}.txt"
            with open(simple_file_path, "w", encoding="utf-8") as f:
                f.write(cover_letter)
            return str(simple_file_path)

    def crawl_job_description(self, job_url):
        """Crawl job description from URL"""
        if not job_url:
            return ""
        return self.web_crawler.fetch_job_description(job_url)

    def app_workflow(self, resume_file, selected_resume, job_description, job_url, company_name, position_name, progress=gr.Progress()):
        """Main workflow for the application"""
        # Store company and position names
        self.company_name = company_name
        self.position_name = position_name
        
        gr.Info("🚀 Starting application workflow...")
        progress(0, desc="Starting...")
        
        # Handle the resume file (either uploaded or selected)
        resume_path = None
        if resume_file:
            # gr.Info("📄 Processing uploaded resume...")
            progress(0.1, desc="Saving uploaded resume...")
            resume_path = self.resume_processor.save_resume(resume_file)
        elif selected_resume:
            resume_path = selected_resume

        if not resume_path:
            gr.Warning("⚠️ No resume provided")
            return "Please upload or select a resume."

        # Check if company name and position name are provided
        if not company_name or not position_name:
            gr.Warning("⚠️ Company name and position name are required")
            return "Please provide both company name and position name."
            
        # Store company and position names
        self.company_name = company_name
        self.position_name = position_name


        # Read resume content
        # gr.Info("📝 Extracting resume content...")
        progress(0.2, desc="Extracting resume content...")
        resume_content = self.resume_processor.extract_text(resume_path)
        if resume_content.startswith("Error"):
            gr.Warning(f"❌ Error processing resume: {resume_content}")
            return resume_content
        
        # Get job description (either from text input or by crawling URL)
        final_job_description = job_description
        if job_url and not job_description:
            gr.Info("🌐 Crawling job description from URL...")
            progress(0.3, desc="Crawling job description from URL...")
            crawled_content = self.crawl_job_description(job_url)
            if crawled_content.startswith("Error"):
                gr.Warning(f"❌ Error crawling job description: {crawled_content}")
                return crawled_content
            
            progress(0.4, desc="Processing job description...")
            final_job_description = self.web_crawler.clean_job_description(crawled_content)
            
            # Check if crawled content is too short
            if len(final_job_description.split()) < 50:  # Arbitrary threshold of 50 words
                gr.Warning("⚠️ Crawled job description seems incomplete or too short. Please consider manually entering the job description for better results.")
        
        if not final_job_description or final_job_description.strip() == "":
            gr.Warning("⚠️ No job description provided")
            return "Please provide a job description or a valid job posting URL."
        
        # Store resume and job description for QnA feature
        self.temp_resume_content = resume_content
        self.temp_job_description = final_job_description
        
        # Generate cover letter
        # gr.Info("✍️ Generating cover letter...")
        progress(0.7, desc="Generating cover letter...")
        cover_letter = self.cover_letter_generator.generate_cover_letter(
            resume_content, final_job_description, company_name, position_name
        )
        
        # Store cover letter temporarily instead of saving it right away
        self.temp_cover_letter = cover_letter
        
        progress(1.0, desc="Done!")
        gr.Info("✅ Cover letter generated successfully!")
        return cover_letter  # Return None for file_output to avoid auto-saving
    
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
    
    def download_qna_file(self, evt=None, data=None):
        """Save and download all Q&A responses"""
        if not self.questions_answers:
            return None
        
        file_path = self.qna_generator.save_qna_response(
            self.questions_answers, 
            self.company_name, 
            self.position_name
        )
        
        if file_path and os.path.exists(file_path):
            return file_path
        return None

    def download_batch_file(self, evt=None, data=None):
        """Save and download batch Q&A responses"""
        return self.download_qna_file()

    def download_cold_mail(self, evt=None, data=None):
        """Save and download the cold mail as a text file"""
        cold_mail = self.cold_mail_generator.temp_cold_mail
        if not cold_mail:
            return None
        
        return self.cold_mail_generator.save_cold_mail(cold_mail, self.company_name, self.position_name)

    def download_linkedin_dm(self, evt=None, data=None):
        """Save and download the LinkedIn DM as a text file"""
        linkedin_dm = self.linkedin_dm_generator.temp_linkedin_dm
        if not linkedin_dm:
            return None
        
        return self.linkedin_dm_generator.save_linkedin_dm(linkedin_dm, self.company_name, self.position_name)

    def download_referral_dm(self, evt=None, data=None):
        """Save and download the referral DM as a text file"""
        referral_dm = self.referral_dm_generator.temp_referral_dm
        if not referral_dm:
            return None
        
        return self.referral_dm_generator.save_referral_dm(referral_dm, self.company_name, self.position_name)

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

    def refresh_resume_templates(self):
        """Refresh the list of available resume templates"""
        return gr.update(
            choices=self.resume_builder.list_resume_templates(),
            value=None
        )

    def build_ui(self):
        """Build the Gradio UI"""
        # Create a custom theme with better colors and fonts
        custom_theme = gr.themes.Soft(
            primary_hue="purple",
            secondary_hue="purple", 
            neutral_hue="zinc",
            # font=("Poppins", "Roboto", "system-ui", "sans-serif"),
            # font_mono=("Fira Code", "ui-monospace", "Consolas", "monospace")
        )
        
        with gr.Blocks(title="Professional Job Application Assistant", theme=custom_theme) as demo:
            # Create a stylish header with custom CSS
            create_header(github_username="subhashbs36", author_name="Subhash")
            
            with gr.Row():
                with gr.Column(scale=3):
                    resume_section, resume_dropdown, refresh_btn, resume_file = create_resume_section(self.resume_processor)                    
                    
                    section, company_name, position_name, job_url, autofill_btn, job_description, generate_btn, reset_btn = create_job_details_section()

                with gr.Column(scale=7):
                    (tabs, cover_letter_output, download_btn, download_output,
                     resume_template, refresh_templates_btn, template_file, resume_sections,
                     user_suggestion, build_resume_btn, resume_latex_preview,
                     pdf_preview, ai_suggestions, fix_latex_pdf_btn, recompile_pdf_btn,
                     download_resume_btn, download_resume_output,
                     application_question, word_limit, answer_btn, answer_output,
                     batch_questions, batch_word_limit, batch_generate_btn, batch_output,
                     batch_download_btn, batch_download_output,
                     clear_qa_btn, download_qa_btn, download_qa_output,
                     qna_history_output,
                     hr_name_email, cold_mail_btn, cold_mail_output,
                     download_cold_mail_btn, download_cold_mail_output,
                     hr_name_linkedin, linkedin_dm_btn, linkedin_dm_output,
                     download_linkedin_dm_btn, download_linkedin_dm_output,
                     referral_name, referral_btn, referral_output,
                     download_referral_btn, download_referral_output, 
                     mail_description, context_source, generate_ai_mail_btn,
                     ai_mail_output, download_ai_mail_btn, download_ai_mail_output ) = create_features_section(self.resume_builder)

                # Create UI elements dictionary
                ui_elements = {
                    'resume_file': resume_file,
                    'resume_dropdown': resume_dropdown,
                    'refresh_btn': refresh_btn,
                    'company_name': company_name,
                    'position_name': position_name,
                    'job_url': job_url,
                    'autofill_btn': autofill_btn,  
                    'job_description': job_description,
                    'generate_btn': generate_btn,
                    'reset_btn': reset_btn,
                    'cover_letter_output': cover_letter_output,
                    'download_btn': download_btn,
                    'download_output': download_output,
                    'application_question': application_question,
                    'word_limit': word_limit,
                    'answer_btn': answer_btn,
                    'answer_output': answer_output,
                    'batch_questions': batch_questions,
                    'batch_word_limit': batch_word_limit,
                    'batch_generate_btn': batch_generate_btn,
                    'batch_output': batch_output,
                    'batch_download_btn': batch_download_btn,
                    'batch_download_output': batch_download_output,
                    'clear_qa_btn': clear_qa_btn,
                    'download_qa_btn': download_qa_btn,
                    'download_qa_output': download_qa_output,
                    'qna_history_output': qna_history_output,
                    'hr_name_email': hr_name_email,
                    'cold_mail_btn': cold_mail_btn,
                    'cold_mail_output': cold_mail_output,
                    'download_cold_mail_btn': download_cold_mail_btn,
                    'download_cold_mail_output': download_cold_mail_output,
                    'hr_name_linkedin': hr_name_linkedin,
                    'linkedin_dm_btn': linkedin_dm_btn,
                    'linkedin_dm_output': linkedin_dm_output,
                    'download_linkedin_dm_btn': download_linkedin_dm_btn,
                    'download_linkedin_dm_output': download_linkedin_dm_output,
                    'referral_name': referral_name,
                    'referral_btn': referral_btn,
                    'referral_output': referral_output,
                    'download_referral_btn': download_referral_btn,
                    'download_referral_output': download_referral_output,
                    'resume_template': resume_template,
                    'refresh_templates_btn': refresh_templates_btn,
                    'template_file': template_file,
                    'resume_sections': resume_sections,
                    'user_suggestion': user_suggestion,
                    'build_resume_btn': build_resume_btn,
                    'resume_latex_preview': resume_latex_preview,
                    'pdf_preview': pdf_preview,
                    'ai_suggestions': ai_suggestions,
                    'fix_latex_pdf_btn': fix_latex_pdf_btn,
                    'recompile_pdf_btn': recompile_pdf_btn,
                    'download_resume_btn': download_resume_btn,
                    'download_resume_output': download_resume_output,
                    'mail_description': mail_description,
                    'context_source': context_source,
                    'generate_ai_mail_btn': generate_ai_mail_btn,
                    'ai_mail_output': ai_mail_output,
                    'download_ai_mail_btn': download_ai_mail_btn,
                    'download_ai_mail_output': download_ai_mail_output
                }

                # Set up event handlers
                setup_event_handlers(self, ui_elements)

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

    def build_optimized_resume(self, template_name, sections, user_suggestion, company_name, position_name):
        """Build an optimized resume based on the selected template and job description"""
        if not self.temp_resume_content or not self.temp_job_description:
            gr.Warning("Please generate a cover letter first to load your resume and job details.")
            return "Please generate a cover letter first to load your resume and job details.", None
        
        if not template_name:
            gr.Warning("Please select a resume template.")
            return "Please select a resume template.", None
        
        if not company_name or not position_name:
            gr.Warning("Please provide both company name and position title.")
            return "Please provide both company name and position title.", None
        
        # Generate optimized resume content
        resume_content = self.resume_builder.generate_resume_content(
            self.temp_resume_content,
            self.temp_job_description,
            sections,
            user_suggestion,
            company_name,
            position_name,
            template_name
        )
        
        # Check if the resume_content is a string (error message)
        if isinstance(resume_content, str) and (resume_content.startswith("Error") or resume_content.startswith("Please")):
            gr.Warning(resume_content)
            return resume_content, None
        
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
                gr.Warning("Failed to compile LaTeX after attempting fixes")
                return resume_content, None
            else:
                gr.Info("✅ LaTeX compilation successful!")
                return resume_content, pdf_path
        else:
            gr.Info("✅ LaTeX compilation successful!")
            return resume_content, pdf_path
        

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
            return None, f"❌ LaTeX Compilation Error:\n\nPlease Run Auto Fix Error"
        
        if file_path and os.path.exists(file_path):
            return file_path, f"✅ LaTeX compilation successful! Click 'Download Resume PDF' to save the file."
        return None, "Failed to generate PDF"

    def latex_code_fixer(self, latex_code, sections, suggestions):
        """Fix LaTeX errors in the provided code"""
        if not latex_code:
            gr.Warning("Please generate resume content first.")
            return None, "<p>No content to fix</p>"

        # Handle suggestions if provided
        if suggestions and suggestions.strip():
            # Incorporate suggestions into the LaTeX code
            latex_code = self.resume_builder.incorporate_suggestions(latex_code, self.temp_resume_content, sections, suggestions)

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
                gr.Warning("Failed to compile LaTeX after attempting fixes")
                return latex_code, None

            gr.Info("✅ Fixed LaTeX errors and compiled successfully!")
            return fixed_latex, file_path

        gr.Info("✅ No errors found in LaTeX code!")
        return latex_code, file_path

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
            None,  # user_suggestion
            "",    # ai_suggestions
        )

    def _autofill_job_details(self, input_text: str, progress=gr.Progress()) -> tuple[str, str]:
        """Autofill job details from URL or text"""
        if input_text.startswith(('http://', 'https://')):
            progress(0.3, desc="Fetching job description from URL...")
            # Use WebCrawler to fetch the job description
            crawled_content = self.web_crawler.fetch_job_description(input_text)
            if crawled_content.startswith("Error"):
                return "", ""
            
            progress(0.6, desc="Cleaning job description...")
            # Clean the job description
            cleaned_content = self.web_crawler.clean_job_description(crawled_content)
            
            progress(0.9, desc="Extracting job details...")
            # Use JobDetailsExtractor with the cleaned content
            details = self.job_extractor.extract_from_text(cleaned_content)
        else:
            progress(0.5, desc="Extracting job details from text...")
            details = self.job_extractor.extract_from_text(input_text)
        
        progress(1.0, desc="Done!")
        return details['company'], details['position']

    def generate_ai_mail(self, description, context_source, resume_file, resume_dropdown, job_description, company_name, position_name):
        """Generate an AI email based on the provided description and context"""
        if not description:
            return "Please provide a description of what you want to communicate."

        # Get resume content if needed
        resume_content = None
        if context_source in ["Resume", "Both"]:
            if resume_file:
                resume_path = self.resume_processor.save_resume(resume_file)
                resume_content = self.resume_processor.extract_text(resume_path)
            elif resume_dropdown:
                resume_content = self.resume_processor.extract_text(resume_dropdown)

            if not resume_content:
                return "Please provide a resume to use as context."

        # Check job description if needed
        if context_source in ["Job Description", "Both"]:
            if not job_description:
                return "Please provide a job description to use as context."

        # Prepare context based on selection, using only verified user information
        context = ""
        if context_source == "None":
            context = "Generate a professional email based only on the provided instructions."
        elif context_source == "Resume":
            # Only use verified information from the user's resume
            context = f"Using only the following verified information from your resume:\n{resume_content}"
        elif context_source == "Job Description":
            context = job_description
        else:  # Both
            # Combine resume and job description while emphasizing use of verified information
            context = f"Using only the following verified information from your resume:\n{resume_content}\n\nJob Description:\n{job_description}"

        # Generate the email
        email_content = self.ai_mail_generator.generate_email(
            description=description,
            context=context,
            company_name=company_name,
            position_name=position_name
        )

        # Store for later use
        self.ai_mail_generator.temp_email = email_content
        return email_content

    def download_ai_mail(self, company_name, position_name, email_content):
        """Save and download the AI-generated email"""
        if not email_content:
            return None

        # Clean file names
        clean_company = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
        clean_position = re.sub(r'[^\w\s-]', '', position_name).strip().replace(' ', '_')
        timestamp = time.strftime("%Y%m%d%H%M%S")
        
        file_name = f"AI_Email_{clean_company}_{clean_position}_{timestamp}.txt"
        file_path = self.ai_mails_path / file_name

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(email_content)
            return str(file_path)
        except Exception as e:
            print(f"Error saving AI email: {e}")
            return None
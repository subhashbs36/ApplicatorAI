import gradio as gr
from gradio_pdf import PDF

def create_header(title="ApplicatorAI", subtitle="AI-Powered Job Application Assistant", 
                 github_username="subhashbs36", repo_name="Applicator", author_name="Subhash",
                 version="1.0.0"):
    """
    Create a customizable header for the application.
    """
    # Use provided values or defaults
    github_username = github_username or "subhashbs36"
    author_name = author_name or "Subhash B S"
    
    # Create a simple markdown header with inline styling to appear as a navbar
    markdown_content = f"""
    <div style="display: flex; flex-direction: column; gap: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0 0 8px 0; margin-top: -10px;">
            <span style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 2.5em; font-weight: bold;">{title}</span>
                <span style="font-weight: normal; font-size: 1.0em; color: #666;">•</span>
                <span style="font-weight: normal; font-size: 1.0em;">{subtitle}</span>
                <span style="font-weight: normal; font-size: 0.9em; color: #666;">v{version}</span>
            </span>
            <span style="display: flex; align-items: center; gap: 12px;">
                <a href="https://github.com/{github_username}/{repo_name}" target="_blank" style="text-decoration: none;">
                    <img src="https://img.shields.io/github/stars/{github_username}/{repo_name}?style=social" alt="GitHub stars">
                </a>
                <a href="https://www.buymeacoffee.com/subhashbs" target="_blank" style="text-decoration: none;">
                    <img src="https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support-orange" alt="Buy Me A Coffee">
                </a>
                <span style="font-size: 0.9em;">Made with ❤️ by <a href="https://github.com/{github_username}" target="_blank" style="text-decoration: underline;">{author_name}</a></span>
            </span>
        </div>
        <div id="version-check" style="display: none; background-color: #fff3cd; color: #856404; padding: 8px; border-radius: 4px; text-align: center;">
            A new version is available! <a href="https://github.com/{github_username}/{repo_name}/releases" target="_blank">Update now</a>
        </div>
        <script>
            async function checkVersion() {{
                try {{
                    const response = await fetch('https://api.github.com/repos/{github_username}/{repo_name}/releases/latest');
                    const data = await response.json();
                    const latestVersion = data.tag_name.replace('v', '');
                    const currentVersion = '{version}';
                    
                    if (latestVersion > currentVersion) {{
                        document.getElementById('version-check').style.display = 'block';
                    }}
                }} catch (error) {{
                    console.error('Error checking version:', error);
                }}
            }}
            checkVersion();
        </script>
    </div>
    """
    
    return gr.HTML(markdown_content)

def create_resume_section(resume_processor):
    with gr.Group() as section:
        gr.Markdown("## Resume")
        with gr.Tab("Existing Resumes"):
            resume_dropdown = gr.Dropdown(
                label="Select Existing Resume", 
                choices=[file_info[0] for file_info in resume_processor.list_resumes()],
                interactive=True            
                )
            refresh_btn = gr.Button("Refresh Resume List", variant="secondary", size="sm")

        with gr.Tab("Upload Resume"):
            resume_file = gr.File(
                label="Upload Resume (PDF, DOC, DOCX, or TXT)",
                file_types=[".pdf", ".doc", ".docx", ".txt"],
                type="filepath"
            )
    return section, resume_dropdown, refresh_btn, resume_file

def create_job_details_section():
    with gr.Group() as section:
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
                placeholder="Enter the URL of the job posting...",
                info="We'll automatically extract the job description from this URL"
            )
                                
        with gr.Tab("Manual Entry"):
            job_description = gr.Textbox(
                label="Job Description", 
                placeholder="Paste the job description here...",
                lines=5,
                max_lines=10,
                info="Full job posting text including requirements and responsibilities"
            )

        with gr.Row(equal_height=True):
            autofill_btn = gr.Button("Get Job Details", variant="secondary", scale=1)
            generate_btn = gr.Button("Generate Cover Letter", variant="primary", scale=1)
            reset_btn = gr.Button("Reset Form", variant="secondary", scale=1)

    return section, company_name, position_name, job_url, autofill_btn, job_description, generate_btn, reset_btn


def create_features_section(resume_builder):
    """Create the features section of the UI"""
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
                        lines=2
                    )
                    word_limit = gr.Textbox(
                        label="Word Limit (Optional)", 
                        placeholder="Enter word limit if specified..."
                    )
                    answer_btn = gr.Button("Generate Answer", variant="primary")
                    answer_output = gr.Textbox(
                        label="Your Answer", 
                        lines=10,
                        show_copy_button=True,
                        interactive=True
                    )
                
                with gr.Tab("Batch Questions"):
                    batch_questions = gr.Textbox(
                        label="Multiple Questions",
                        placeholder="Enter one question per line...",
                        lines=10
                    )
                    batch_word_limit = gr.Textbox(
                        label="Word Limit (Optional)",
                        placeholder="Enter word limit if specified..."
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
                gr.Markdown("Generate personalized cold mails and LinkedIn messages to hiring managers based on your resume and the job description.")
                
                # Move hr_name inside the tabs that need it
                with gr.Tab("Cold Mail"):
                    hr_name_email = gr.Textbox(
                        label="Hiring Manager/Recruiter Name (Optional)", 
                        placeholder="Enter the name of the hiring manager or recruiter if known...",
                        info="Leave blank to use a generic greeting"
                    )
                    
                    cold_mail_btn = gr.Button("Generate Cold Mail", variant="primary")
                    
                    cold_mail_output = gr.Textbox(
                        label="Your Cold Mail", 
                        lines=12,
                        show_copy_button=True,
                        info="Your personalized cold mail will appear here. Feel free to edit before downloading.",
                        interactive=True  # Make the textbox editable
                    )
                    
                    download_cold_mail_btn = gr.Button("Download Cold Mail", variant="secondary")
                    download_cold_mail_output = gr.File(label="Download Mail")
                
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
                
                # Add new AI Mail Generator tab
                with gr.Tab("AI Mail Generator"):
                    mail_description = gr.Textbox(
                        label="Email Description", 
                        placeholder="Enter a brief description of what you want to communicate...",
                        lines=3,
                        info="Describe the purpose and context of your email"
                    )
                    
                    context_source = gr.Radio(
                        choices=["None", "Resume", "Job Description", "Both"],
                        value="None",
                        label="Reference Source",
                        info="Choose which document(s) to use as context for generating the email (select 'None' for a generic email)"
                    )
                    
                    generate_ai_mail_btn = gr.Button("Generate Email", variant="primary")
                    
                    ai_mail_output = gr.Textbox(
                        label="Generated Email", 
                        lines=12,
                        show_copy_button=True,
                        info="Your AI-generated email will appear here. Feel free to edit before copying or downloading for reference.",
                        interactive=True
                    )
                    
                    download_ai_mail_btn = gr.Button("Download AI Email", variant="secondary")
                    download_ai_mail_output = gr.File(label="Download Email")                

        # Add new Resume Builder tab
        with gr.TabItem("Resume Builder"):
            with gr.Group():
                gr.Markdown("## ATS-Friendly Resume Builder")
                gr.Markdown("Generate a tailored resume optimized for the job description using LaTeX templates.")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        with gr.Tab("Existing Template"):
                            resume_template = gr.Dropdown(
                                label="Resume Template",
                                choices=resume_builder.list_templates(),  # Use passed resume_builder
                                interactive=True,
                                info="Choose a LaTeX template for your resume"
                            )
                        
                            refresh_templates_btn = gr.Button("Refresh Templates", variant="secondary", size="sm")
                                
                        with gr.Tab("Upload Template"):
                            template_file = gr.File(
                                label="Upload Template (TEX)",
                                file_types=[".tex"],
                                type="filepath"
                            )

                    with gr.Column(scale=1):
                        resume_sections = gr.CheckboxGroup(
                            label="Resume Sections to Include",
                            choices=["Education", "Experience", "Skills", "Projects", "Certifications", "Publications", "Awards"],
                            value=["Education", "Experience", "Skills"],
                            info="Select which sections to include in your resume"
                        )
                    
                    # with gr.Column(scale=1):
                    #     user_suggestion = gr.Textbox(
                    #         label="Keywords to Highlight (Optional)", 
                    #         placeholder="Enter keywords from the job description to emphasize in your resume...",
                    #         info="Separate keywords with commas"
                    #     )

                user_suggestion = gr.Textbox(
                    label="Additional Suggestions (Optional)", 
                    placeholder="Enter any additional suggestions or requirements for your resume...",
                    info="Add any specific formatting or content suggestions",
                    lines=3
                )
                        
                build_resume_btn = gr.Button("Build Optimized Resume", variant="primary")
                
                with gr.Row():
                    with gr.Column(scale=4):
                        resume_latex_preview = gr.Textbox(
                            label="LaTeX Code", 
                            lines=20,
                            show_copy_button=True,
                            info="LaTeX code for your resume",
                            interactive=True
                        )
                        ai_suggestions = gr.Textbox(
                            label="AI Suggestions & Corrections (Optional)", 
                            lines=5,
                            show_copy_button=True,
                            info="Enter your corrections or suggestions to improve the resume",
                            interactive=True,
                            placeholder="Enter any corrections or suggestions to improve the resume content..."
                        )

                    with gr.Column(scale=6):                                
                        pdf_preview = PDF(
                            label="PDF Preview",
                            visible=True,
                            interactive=True
                        )
                
                with gr.Row():
                    with gr.Column(scale=1):
                        fix_latex_pdf_btn = gr.Button("Generate/Fix Error", variant="primary")
                    with gr.Column(scale=1):
                        recompile_pdf_btn = gr.Button("ReCompile", variant="primary")
                    
                    with gr.Column(scale=1):
                        download_resume_btn = gr.Button("Download Resume PDF", variant="primary")
                        download_resume_output = gr.File(label="Download Resume")



    return (
        tabs, cover_letter_output, download_btn, download_output,
        resume_template, refresh_templates_btn, template_file, resume_sections,  # Added template_file
        user_suggestion, build_resume_btn, resume_latex_preview,
        pdf_preview, ai_suggestions, fix_latex_pdf_btn, recompile_pdf_btn,
        download_resume_btn, download_resume_output,
        # Add Q&A components
        application_question, word_limit, answer_btn, answer_output,
        batch_questions, batch_word_limit, batch_generate_btn, batch_output,
        batch_download_btn, batch_download_output,
        clear_qa_btn, download_qa_btn, download_qa_output,
        qna_history_output,
        # Add outreach components
        hr_name_email, cold_mail_btn, cold_mail_output,
        download_cold_mail_btn, download_cold_mail_output,
        hr_name_linkedin, linkedin_dm_btn, linkedin_dm_output,
        download_linkedin_dm_btn, download_linkedin_dm_output,
        referral_name, referral_btn, referral_output,
        download_referral_btn, download_referral_output,
        mail_description, context_source, generate_ai_mail_btn,
        ai_mail_output, download_ai_mail_btn, download_ai_mail_output
    )

def setup_event_handlers(app, ui_elements):
    """Set up all event handlers for the UI"""
    # Extract UI elements from dictionary
    autofill_btn = ui_elements['autofill_btn']
    generate_btn = ui_elements['generate_btn']
    download_btn = ui_elements['download_btn']
    refresh_btn = ui_elements['refresh_btn']
    reset_btn = ui_elements['reset_btn']
    resume_file = ui_elements['resume_file']
    resume_dropdown = ui_elements['resume_dropdown']
    job_description = ui_elements['job_description']
    job_url = ui_elements['job_url']
    company_name = ui_elements['company_name']
    position_name = ui_elements['position_name']
    cover_letter_output = ui_elements['cover_letter_output']
    download_output = ui_elements['download_output']
    
    # Extract Q&A elements
    application_question = ui_elements['application_question']
    word_limit = ui_elements['word_limit']
    answer_btn = ui_elements['answer_btn']
    answer_output = ui_elements['answer_output']
    batch_questions = ui_elements['batch_questions']
    batch_word_limit = ui_elements['batch_word_limit']
    batch_generate_btn = ui_elements['batch_generate_btn']
    batch_output = ui_elements['batch_output']
    batch_download_btn = ui_elements['batch_download_btn']
    batch_download_output = ui_elements['batch_download_output']
    clear_qa_btn = ui_elements['clear_qa_btn']
    download_qa_btn = ui_elements['download_qa_btn']
    download_qa_output = ui_elements['download_qa_output']
    qna_history_output = ui_elements['qna_history_output']

    # Extract outreach elements
    hr_name_email = ui_elements['hr_name_email']
    cold_mail_btn = ui_elements['cold_mail_btn']
    cold_mail_output = ui_elements['cold_mail_output']
    download_cold_mail_btn = ui_elements['download_cold_mail_btn']
    download_cold_mail_output = ui_elements['download_cold_mail_output']
    hr_name_linkedin = ui_elements['hr_name_linkedin']
    linkedin_dm_btn = ui_elements['linkedin_dm_btn']
    linkedin_dm_output = ui_elements['linkedin_dm_output']
    download_linkedin_dm_btn = ui_elements['download_linkedin_dm_btn']
    download_linkedin_dm_output = ui_elements['download_linkedin_dm_output']
    referral_name = ui_elements['referral_name']
    referral_btn = ui_elements['referral_btn']
    referral_output = ui_elements['referral_output']
    download_referral_btn = ui_elements['download_referral_btn']
    download_referral_output = ui_elements['download_referral_output']

    # Extract AI Mail Generator elements
    mail_description = ui_elements['mail_description']
    context_source = ui_elements['context_source']
    generate_ai_mail_btn = ui_elements['generate_ai_mail_btn']
    ai_mail_output = ui_elements['ai_mail_output']
    download_ai_mail_btn = ui_elements['download_ai_mail_btn']
    download_ai_mail_output = ui_elements['download_ai_mail_output']

    # Extract resume builder elements
    resume_template = ui_elements['resume_template']
    refresh_templates_btn = ui_elements['refresh_templates_btn']
    template_file = ui_elements['template_file']  
    resume_sections = ui_elements['resume_sections']
    user_suggestion = ui_elements['user_suggestion']
    build_resume_btn = ui_elements['build_resume_btn']
    resume_latex_preview = ui_elements['resume_latex_preview']
    pdf_preview = ui_elements['pdf_preview']
    ai_suggestions = ui_elements['ai_suggestions']
    fix_latex_pdf_btn = ui_elements['fix_latex_pdf_btn']
    recompile_pdf_btn = ui_elements['recompile_pdf_btn']
    download_resume_btn = ui_elements['download_resume_btn']
    download_resume_output = ui_elements['download_resume_output']

    # Connect the autofill button
    autofill_btn.click(
        fn=app._autofill_job_details,
        inputs=[job_url],
        outputs=[company_name, position_name] 
    )

    # Set up event handlers
    generate_btn.click(
        fn=app.app_workflow,
        inputs=[
            resume_file,
            resume_dropdown,
            job_description,
            job_url,
            company_name,
            position_name
        ],
        outputs=[cover_letter_output]
    )
    
    # Update event handlers to pass current content
    download_btn.click(
        fn=app.download_file,
        inputs=[company_name, position_name, cover_letter_output],
        outputs=download_output
    )
    
    refresh_btn.click(
        fn=app.refresh_resume_list,
        inputs=[],
        outputs=resume_dropdown
    )
    
    # Add reset button handler
    reset_btn.click(
        fn=app.reset_form,
        inputs=[],
        outputs=[
            job_description, job_url, company_name, position_name, cover_letter_output,
            application_question, word_limit, answer_output, batch_questions, batch_word_limit,
            batch_output, hr_name_email, cold_mail_output,
            hr_name_linkedin, linkedin_dm_output, referral_name, referral_output,
            qna_history_output, mail_description, ai_mail_output  # Add new components
        ]
    )
    
    # Q&A tab functionality
    answer_btn.click(
        fn=app.generate_qna_answer,
        inputs=[application_question, word_limit, company_name, position_name],
        outputs=answer_output
    )
    
    clear_qa_btn.click(
        fn=app.clear_qna_history,
        inputs=[],
        outputs=qna_history_output
    )
    
    download_qa_btn.click(
        fn=app.download_qna_file,
        inputs=[company_name, position_name, qna_history_output],
        outputs=download_qa_output
    )
    
    # Update Q&A history whenever a new answer is generated
    answer_btn.click(
        fn=app.update_qna_history,
        inputs=[],
        outputs=qna_history_output
    )
    
    # Batch Q&A tab functionality
    batch_generate_btn.click(
        fn=app.generate_batch_answers,
        inputs=[batch_questions, batch_word_limit, company_name, position_name],
        outputs=batch_output
    )
    
    batch_download_btn.click(
        fn=app.download_batch_file,
        inputs=[company_name, position_name, batch_output],
        outputs=batch_download_output
    )
    
    # New tab for Cold Mail and LinkedIn DM
    cold_mail_btn.click(
        fn=app.generate_cold_mail,
        inputs=[hr_name_email, company_name, position_name],
        outputs=cold_mail_output
    )
    
    download_cold_mail_btn.click(
        fn=app.download_cold_mail,
        inputs=[company_name, position_name, cold_mail_output],
        outputs=download_cold_mail_output
    )
    
    linkedin_dm_btn.click(
        fn=app.generate_linkedin_dm,
        inputs=[hr_name_linkedin, company_name, position_name],
        outputs=linkedin_dm_output
    )
    
    download_linkedin_dm_btn.click(
        fn=app.download_linkedin_dm,
        inputs=[company_name, position_name, linkedin_dm_output],
        outputs=download_linkedin_dm_output
    )

    download_referral_btn.click(
        fn=app.download_referral_dm,
        inputs=[company_name, position_name, referral_output],
        outputs=download_referral_output
    )

    # Add Resume Builder event handlers
    refresh_templates_btn.click(
        fn=app.resume_builder.list_templates,
        inputs=[],
        outputs=resume_template
    )
    
    # Add template upload handler
    template_file.upload(
        fn=app.resume_builder.add_template,
        inputs=[template_file]
    ).then(
        fn=app.refresh_resume_templates,
        outputs=resume_template
    )

    # Update the build_resume_btn click handler to output to both preview components
    build_resume_btn.click(
        fn=app.build_optimized_resume,
        inputs=[
            resume_template,
            resume_sections,
            user_suggestion,
            company_name,
            position_name
        ],
        outputs=[resume_latex_preview, pdf_preview]
    )
    
    # Add a handler for the recompile_pdf_btn
    recompile_pdf_btn.click(
        fn=app.latex_compiler,
        inputs=[resume_latex_preview],
        outputs=[pdf_preview]  # Update both outputs
    )

    fix_latex_pdf_btn.click(
        fn=app.latex_code_fixer,
        inputs=[resume_latex_preview, resume_sections, ai_suggestions],
        outputs=[resume_latex_preview, pdf_preview]
    )

    # Update the download_resume_btn click handler
    download_resume_btn.click(
        fn=app.download_resume,
        inputs=[company_name, position_name, resume_latex_preview, resume_template],
        outputs=download_resume_output
    )
    
    # Add referral button handler that was missing
    referral_btn.click(
        fn=app.generate_referral_dm,
        inputs=[referral_name, company_name, position_name],
        outputs=referral_output
    )

    # Add AI Mail Generator event handlers
    generate_ai_mail_btn.click(
        fn=app.generate_ai_mail,
        inputs=[
            mail_description,
            context_source,
            resume_file,
            resume_dropdown,
            company_name,
            position_name
        ],
        outputs=ai_mail_output
    )

    download_ai_mail_btn.click(
        fn=app.download_ai_mail,
        inputs=[company_name, position_name, ai_mail_output],
        outputs=download_ai_mail_output
    )

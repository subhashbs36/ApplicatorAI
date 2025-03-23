import os
import gradio as gr
import re
from datetime import date
from dotenv import load_dotenv
import fpdf
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Create resume directory if it doesn't exist
os.makedirs("resumes", exist_ok=True)

def save_resume(file):
    """Save uploaded resume to the resumes directory"""
    if file is None:
        return None
    file_path = os.path.join("resumes", file.name)
    with open(file_path, "wb") as f:
        f.write(file.read())
    return file_path

def read_file(file_path):
    """Read file content"""
    if not file_path or not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def list_resumes():
    """List all resume files in the resumes directory"""
    if not os.path.exists("resumes"):
        return []
    return [os.path.join("resumes", f) for f in os.listdir("resumes") if os.path.isfile(os.path.join("resumes", f))]

def truncate_text(text, max_chars=2000):
    """Truncate text to stay within token limits"""
    if len(text) <= max_chars:
        return text
    
    # Simple truncation for now
    return text[:max_chars] + "...[content truncated due to length]"

def generate_cover_letter(resume_content, job_description, company_name, position_name):
    """Generate cover letter using Gemini API"""
    if not resume_content:
        return "Please upload or select a resume first."
    
    if not job_description:
        return "Please provide a job description."
    
    if not company_name:
        return "Please provide the company name."
    
    if not position_name:
        return "Please provide the position name."
    
    today = date.today().strftime("%B %d, %Y")
    
    # Only truncate job description if necessary, but keep full resume
    # processed_job = truncate_text(job_description, 2500)
    processed_job = job_description
    
    # Create the prompt for Gemini
    prompt = f"""
    You are a professional cover letter writer. Based on the resume and job description provided, create a compelling cover letter.
    
    Resume:
    {resume_content}
    
    Job Description:
    {processed_job}
    
    Create a cover letter for a {position_name} position at {company_name} with the following structure:
    
    1. Start with today's date ({today})
    2. Include "Hiring Manager" and {company_name} in the header
    3. Begin with "Dear Hiring Manager,"
    4. Write a compelling opening paragraph that specifically mentions the {position_name} position at {company_name}
    5. In the body paragraphs, directly connect 2-3 specific achievements from the resume to the requirements in the job description
    6. Explain specifically why the candidate is interested in {company_name} (research their mission or recent projects)
    7. Include a strong closing paragraph with contact information from the resume
    8. End with "Sincerely," followed by the full name from the resume
    
    DO NOT include any Links, placeholder text or instructions in the final cover letter.
    """
    
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Generate the cover letter
        response = model.generate_content(prompt)
        
        # Process the response to ensure the template format
        cover_letter = response.text.strip()
        
        # Ensure the date is included
        if today not in cover_letter:
            cover_letter = today + "\n\n" + cover_letter
        
        # Ensure company name is included
        if company_name not in cover_letter:
            match = re.search(r'Dear .+,', cover_letter)
            if match:
                idx = match.end()
                cover_letter = cover_letter[:idx] + f"\n\n{company_name}\n" + cover_letter[idx:]
        
        return cover_letter
    
    except Exception as e:
        # Handle API errors gracefully
        error_message = str(e)
        return f"Error generating cover letter: {error_message}"

def create_pdf(cover_letter, file_path):
    """Create a PDF document from the cover letter text"""
    pdf = fpdf.FPDF()
    pdf.add_page()
    
    # Set up fonts
    pdf.set_font("Arial", "", 12)
    
    # Add content
    lines = cover_letter.split('\n')
    for line in lines:
        if not line.strip():  # Add some space for empty lines
            pdf.ln(10)
        elif line.startswith("Dear ") or line.startswith("Sincerely,"):
            # Format salutation and closing with extra space
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, line, 0, 1)
            pdf.ln(5)
        elif len(line) < 30 and line.strip() == line:
            # Likely a header or date
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, line, 0, 1)
        else:
            # Regular paragraph text
            pdf.set_font("Arial", "", 12)
            pdf.multi_cell(0, 10, line)
    
    # Save the PDF
    pdf.output(file_path)

def save_cover_letter(cover_letter, company_name, position_name):
    """Save the cover letter to a PDF file"""
    if not cover_letter or cover_letter.startswith("Please ") or cover_letter.startswith("Error"):
        return "No valid cover letter to save."
    
    # Clean file name - Fix for the invalid filename error
    clean_company = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
    clean_position = re.sub(r'[^\w\s-]', '', position_name).strip().replace(' ', '_')
    
    # Replace any problematic characters and ensure the filename is valid
    clean_company = re.sub(r'\s+', '_', clean_company)
    clean_position = re.sub(r'\s+', '_', clean_position)
    
    # Make sure the filename doesn't have any other problematic characters
    file_name = f"Cover_Letter_{clean_company}_{clean_position}.pdf"
    
    # Create directory if it doesn't exist
    os.makedirs("cover_letters", exist_ok=True)
    file_path = os.path.join("cover_letters", file_name)
    
    try:
        # Create PDF file
        create_pdf(cover_letter, file_path)
        return file_path
    except Exception as e:
        print(f"Error creating PDF: {e}")
        # Fallback to text file if PDF creation fails
        txt_file_path = os.path.join("cover_letters", f"Cover_Letter_{clean_company}_{clean_position}.txt")
        with open(txt_file_path, "w", encoding="utf-8") as f:
            f.write(cover_letter)
        return txt_file_path

def app_workflow(resume_file, selected_resume, job_description, company_name, position_name):
    """Main workflow for the application"""
    # Handle the resume file (either uploaded or selected)
    resume_path = None
    if resume_file:
        resume_path = save_resume(resume_file)
    elif selected_resume:
        resume_path = selected_resume
    
    if not resume_path:
        return "Please upload or select a resume.", None
    
    # Read resume content
    resume_content = read_file(resume_path)
    
    # Generate cover letter with full resume content
    cover_letter = generate_cover_letter(resume_content, job_description, company_name, position_name)
    
    # Save cover letter
    if not cover_letter.startswith("Please ") and not cover_letter.startswith("Error"):
        save_path = save_cover_letter(cover_letter, company_name, position_name)
        return cover_letter, save_path
    
    return cover_letter, None

def download_file(file_path):
    """Function to return file for downloading"""
    if not file_path or file_path.startswith("No valid"):
        return None
    return file_path

with gr.Blocks(title="Cover Letter Generator") as demo:
    gr.Markdown("# Professional Cover Letter Generator")
    gr.Markdown("Upload your resume, provide job details, and generate a customized cover letter.")
    
    with gr.Row():
        with gr.Column(scale=1):
            with gr.Tab("Upload Resume"):
                resume_file = gr.File(label="Upload Resume")
            
            with gr.Tab("Existing Resumes"):
                resume_dropdown = gr.Dropdown(
                    label="Select Existing Resume", 
                    choices=list_resumes(),
                    interactive=True,
                    every=1  # Refresh the list every 1 second
                )
            
            gr.Markdown("## Job Details")
            company_name = gr.Textbox(label="Company Name", placeholder="Enter company name...")
            position_name = gr.Textbox(label="Position Title", placeholder="Enter position title...")
            job_description = gr.Textbox(
                label="Job Description", 
                placeholder="Paste the job description here...",
                lines=10
            )
            
            generate_btn = gr.Button("Generate Cover Letter", variant="primary")
        
        with gr.Column(scale=1):
            gr.Markdown("## Generated Cover Letter")
            cover_letter_output = gr.Textbox(
                label="Your Cover Letter", 
                lines=20,
                show_copy_button=True
            )
            
            file_output = gr.Textbox(label="Saved File", visible=False)
            
            download_btn = gr.Button("Download Cover Letter as PDF")
    
    # Set up event handlers
    generate_btn.click(
        fn=app_workflow,
        inputs=[resume_file, resume_dropdown, job_description, company_name, position_name],
        outputs=[cover_letter_output, file_output]
    )
    
    # Fixed download button functionality
    download_btn.click(
        fn=download_file,
        inputs=[file_output],
        outputs=[gr.File(label="Download")]
    )
    
    # Clear resume upload when an existing resume is selected
    resume_dropdown.change(lambda x: None, inputs=[], outputs=[resume_file])
    
    # Refresh resume list when a new resume is uploaded
    resume_file.change(
        fn=lambda: gr.update(choices=list_resumes()),
        inputs=[],
        outputs=[resume_dropdown]
    )

if __name__ == "__main__":
    demo.launch()
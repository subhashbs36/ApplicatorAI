# Use slim Python image
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (LaTeX + required utilities)
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-latex-extra \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories in one go
RUN mkdir -p /app/src/data/{cache,responses/ai_mails,responses/cold_mails,\
responses/cover_letters,responses/generated_pdfs,responses/generated_resumes,\
responses/linkedin_dms,responses/qna_responses,resume_templates,user_resume}

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=7860
ENV PATH="/root/.local/bin:$PATH"

# Expose the port for Gradio
EXPOSE 7860

# Set default command
ENTRYPOINT ["python", "app.py"]

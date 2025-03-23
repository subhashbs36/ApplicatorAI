import os
import re
from pathlib import Path
import PyPDF2
import docx2txt
import time

class ResumeProcessor:
    """Class to handle resume processing operations"""
    
    @staticmethod
    def save_resume(file):
        """Save uploaded resume to the resumes directory"""
        if file is None:
            return None
            
        # In Gradio, 'file' is typically a tuple or dictionary with file information
        # For file upload components with type="binary", it should be a tuple of (file path, file object, file name)
        # For file upload components with type="filepath", it would just be the file path
        
        if isinstance(file, (tuple, list)) and len(file) >= 3:
            # Handling file as (path, file, name) tuple from gradio
            file_path, file_obj, original_name = file[:3]
        elif isinstance(file, dict) and 'name' in file:
            # Alternative format that might be returned
            file_path = file.get('path')
            original_name = file.get('name')
        elif isinstance(file, str):
            # In case it's just a filepath
            file_path = file
            original_name = os.path.basename(file)
        else:
            return None
        
        # Create a safe filename
        safe_name = re.sub(r'[^\w\s.-]', '', original_name) # type: ignore
        dest_path = os.path.join("resumes", safe_name)
        
        # If we have a file path, just copy the file
        if file_path and os.path.exists(file_path):
            import shutil
            shutil.copy2(file_path, dest_path)
            return dest_path
        
        # Otherwise, we might need to read from the file object
        # This would be less common in Gradio's default setup
        if hasattr(file, 'read') and callable(file.read):
            with open(dest_path, "wb") as f:
                f.write(file.read())
            return dest_path
        
        return None
    
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

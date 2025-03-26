import os
import re
from pathlib import Path
import PyPDF2
import docx2txt
import time

class ResumeProcessor:
    """Class to handle resume processing operations"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent.parent.parent.parent
        self.data_path = self.base_path / "src" /"data"
        self.resume_path = self.data_path / "user_resume"
        # Create resume directory if it doesn't exist
        self.resume_path.mkdir(parents=True, exist_ok=True)

    def save_resume(self, file):
        """Save uploaded resume to the resumes directory"""
        if file is None:
            return None
            
        if isinstance(file, (tuple, list)) and len(file) >= 3:
            file_path, file_obj, original_name = file[:3]
        elif isinstance(file, dict) and 'name' in file:
            file_path = file.get('path')
            original_name = file.get('name')
        elif isinstance(file, str):
            file_path = file
            original_name = os.path.basename(file)
        else:
            return None
        
        # Create a safe filename
        safe_name = re.sub(r'[^\w\s.-]', '', original_name)
        dest_path = self.resume_path / safe_name
        
        # If we have a file path, just copy the file
        if file_path and os.path.exists(file_path):
            import shutil
            shutil.copy2(file_path, str(dest_path))
            return str(dest_path)
        
        # Otherwise, we might need to read from the file object
        if hasattr(file, 'read') and callable(file.read):
            with open(dest_path, "wb") as f:
                f.write(file.read())
            return str(dest_path)
        
        return None

    def list_resumes(self):
        """List all resume files in the resumes directory"""
        if not self.resume_path.exists():
            return []
            
        files = []
        for f in self.resume_path.iterdir():
            if f.is_file():
                # Add file info including last modified time
                mod_time = f.stat().st_mtime
                mod_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mod_time))
                size_kb = f.stat().st_size / 1024
                display_name = f"{f.name} ({mod_time_str}, {size_kb:.1f} KB)"
                files.append((str(f), display_name))
                
        # Sort by most recent
        files.sort(key=lambda x: os.path.getmtime(x[0]), reverse=True)
        return files

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

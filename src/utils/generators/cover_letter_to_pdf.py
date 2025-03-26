import PyPDF2
import docx2txt
from datetime import date
import fpdf


class PDFGenerator:
    """Class to handle PDF document generation"""
    @staticmethod
    def create_pdf(cover_letter, output_path):
        """Create a professional-looking PDF document from the cover letter text"""
        pdf = fpdf.FPDF()
        pdf.add_page()
        
        # Reduced margins for better fit (left, top, right)
        pdf.set_margins(15, 15, 15)
        
        # Slightly smaller font size to fit more content on one page
        pdf.set_font("Arial", "", 10)
        
        # Replace smart quotes and other special characters with ASCII equivalents
        cover_letter = cover_letter.replace('\u2018', "'").replace('\u2019', "'")  # Smart single quotes
        cover_letter = cover_letter.replace('\u201c', '"').replace('\u201d', '"')  # Smart double quotes
        cover_letter = cover_letter.replace('\u2013', '-').replace('\u2014', '--')  # En and em dashes
        cover_letter = cover_letter.replace('\u2026', '...')  # Ellipsis
        
        # Add content
        lines = cover_letter.split('\n')  # Split by newline
        in_paragraph = False
        
        for line in lines:
            # Handle empty lines
            if not line.strip():
                pdf.ln(6)  # Smaller line break for compactness
                in_paragraph = False
                continue
            
            # Format different parts of the letter
            if line.strip() == date.today().strftime("%B %d, %Y"):
                # Date
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 8, line, 0, 1)
                pdf.ln(2)
            elif line.startswith("Dear ") or line.startswith("Sincerely,"):
                # Salutation and closing
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 6, line, 0, 1)
                pdf.ln(2)
                in_paragraph = False
            elif len(line) < 30 and not in_paragraph:
                # Likely a header or name
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 6, line, 0, 1)
                in_paragraph = False
            else:
                # Regular paragraph text
                pdf.set_font("Arial", "", 10)
                safe_line = ''.join(char if ord(char) < 128 else '?' for char in line)  # Replace non-ASCII chars
                if in_paragraph:
                    pdf.multi_cell(0, 5, safe_line)  # Reduced line height for compactness
                else:
                    pdf.multi_cell(0, 5, safe_line)
                    in_paragraph = True
        
        # Save the PDF
        try:
            pdf.output(output_path)
            return True
        except Exception as e:
            print(f"Error saving PDF: {str(e)}")
            try:
                simple_pdf = fpdf.FPDF()
                simple_pdf.add_page()
                simple_pdf.set_font("Arial", "", 10)
                ascii_text = cover_letter.encode('ascii', 'replace').decode('ascii')
                simple_pdf.multi_cell(0, 5, ascii_text)
                simple_pdf.output(output_path)
                return True
            except Exception as e_fallback:
                print(f"Fallback PDF save also failed: {str(e_fallback)}")
                return False
import pdfplumber
import fitz  # pymupdf
import re

class PDFExtractor:
    def extract(self, pdf_path: str) -> dict:
        """
        Extract text with structure awareness.
        Returns dict with sections and their content.
        """
        sections = {}
        current_section = "preamble"
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Detect headings (numbered, caps, bold patterns)
                    if self._is_heading(line):
                        current_section = line
                        sections[current_section] = ""
                    else:
                        if current_section not in sections:
                            sections[current_section] = ""
                        sections[current_section] += " " + line

        return sections

    def _is_heading(self, line: str) -> bool:
        patterns = [
            r'^\d+[\.\)]\s+[A-Z]',           # 1. HEADING or 1) Heading
            r'^[A-Z][A-Z\s]{4,}$',            # ALL CAPS LINE
            r'^\d+\.\d+[\.\s]+[A-Z]',         # 1.1 Sub heading
            r'^(Chapter|Section|Part|Article|Schedule|Clause)\s+\d+',
            r'^[IVXLC]+\.\s+[A-Z]',           # Roman numerals
        ]
        return any(re.match(p, line) for p in patterns)
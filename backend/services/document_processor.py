import os
from typing import Tuple, Optional

class DocumentProcessor:
    """Process documents and extract text"""
    
    def extract_text(self, file_path: str, file_type: str) -> Tuple[str, int]:
        """
        Extract text from document
        Returns: (extracted_text, page_count)
        """
        if file_type == "pdf":
            return self._extract_from_pdf(file_path)
        elif file_type == "docx":
            return self._extract_from_docx(file_path)
        elif file_type == "txt":
            return self._extract_from_txt(file_path)
        else:
            return "", 0
    
    def _extract_from_pdf(self, file_path: str) -> Tuple[str, int]:
        """Extract text from PDF using PyMuPDF or fallback"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            page_count = len(doc)
            doc.close()
            return text, page_count
        except ImportError:
            # Fallback to PyPDF2
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                return text, len(reader.pages)
            except ImportError:
                # No PDF library available, return empty
                return self._read_raw(file_path), 1
    
    def _extract_from_docx(self, file_path: str) -> Tuple[str, int]:
        """Extract text from DOCX"""
        try:
            from docx import Document
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            # Estimate page count (roughly 3000 chars per page)
            page_count = max(1, len(text) // 3000)
            return text, page_count
        except ImportError:
            return self._read_raw(file_path), 1
    
    def _extract_from_txt(self, file_path: str) -> Tuple[str, int]:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            page_count = max(1, len(text) // 3000)
            return text, page_count
        except Exception:
            return "", 1
    
    def _read_raw(self, file_path: str) -> str:
        """Read file as raw bytes for fallback"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            # Try to decode as text
            try:
                return content.decode('utf-8')
            except:
                return content.decode('latin-1', errors='ignore')
        except:
            return ""

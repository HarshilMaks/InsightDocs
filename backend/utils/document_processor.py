"""Document processing utilities."""
from typing import Dict, Any, List
import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx", ".pptx"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class DocumentProcessor:
    """Handles document parsing and transformation."""

    async def parse_document(self, file_path: str) -> Dict[str, Any]:
        """Parse a document and extract text content."""
        file_path_obj = Path(file_path)
        file_ext = file_path_obj.suffix.lower()

        parsers = {
            ".txt": self._parse_text_file,
            ".pdf": self._parse_pdf_file,
            ".docx": self._parse_word_file,
            ".pptx": self._parse_pptx_file,
        }

        parser = parsers.get(file_ext)
        if not parser:
            return {
                "text": "",
                "metadata": {"error": f"Unsupported file type: {file_ext}"}
            }
        return await parser(file_path)

    async def _parse_text_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            return {
                "text": text,
                "metadata": {"type": "text", "char_count": len(text)}
            }
        except Exception as e:
            logger.error(f"Error parsing text file: {e}")
            return {"text": "", "metadata": {"error": str(e)}}

    async def _parse_pdf_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a PDF file using PyPDF2."""
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(file_path)
            pages = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)

            text = "\n\n".join(pages)
            return {
                "text": text,
                "metadata": {
                    "type": "pdf",
                    "page_count": len(reader.pages),
                    "char_count": len(text),
                }
            }
        except Exception as e:
            logger.error(f"Error parsing PDF file: {e}")
            return {"text": "", "metadata": {"error": str(e)}}

    async def _parse_word_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a Word document using python-docx."""
        try:
            from docx import Document

            doc = Document(file_path)
            parts: List[str] = []

            # Extract paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    parts.append(para.text)

            # Extract table content
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    )
                    if row_text:
                        parts.append(row_text)

            text = "\n\n".join(parts)
            return {
                "text": text,
                "metadata": {
                    "type": "docx",
                    "paragraph_count": len(doc.paragraphs),
                    "table_count": len(doc.tables),
                    "char_count": len(text),
                }
            }
        except Exception as e:
            logger.error(f"Error parsing Word file: {e}")
            return {"text": "", "metadata": {"error": str(e)}}

    async def _parse_pptx_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a PowerPoint file using python-pptx."""
        try:
            from pptx import Presentation

            prs = Presentation(file_path)
            slides_text: List[str] = []

            for i, slide in enumerate(prs.slides, 1):
                slide_parts: List[str] = []
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for para in shape.text_frame.paragraphs:
                            if para.text.strip():
                                slide_parts.append(para.text.strip())
                    if shape.has_table:
                        for row in shape.table.rows:
                            row_text = " | ".join(
                                cell.text.strip() for cell in row.cells if cell.text.strip()
                            )
                            if row_text:
                                slide_parts.append(row_text)
                if slide_parts:
                    slides_text.append(f"[Slide {i}]\n" + "\n".join(slide_parts))

            text = "\n\n".join(slides_text)
            return {
                "text": text,
                "metadata": {
                    "type": "pptx",
                    "slide_count": len(prs.slides),
                    "char_count": len(text),
                }
            }
        except Exception as e:
            logger.error(f"Error parsing PPTX file: {e}")
            return {"text": "", "metadata": {"error": str(e)}}

    async def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[str]:
        """Split text into overlapping chunks."""
        if not text:
            return []

        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk: List[str] = []
        current_size = 0

        for sentence in sentences:
            sentence_size = len(sentence)

            if current_size + sentence_size > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                # Keep trailing sentences for overlap
                overlap_chunk: List[str] = []
                overlap_size = 0
                for s in reversed(current_chunk):
                    if overlap_size + len(s) > overlap:
                        break
                    overlap_chunk.insert(0, s)
                    overlap_size += len(s)
                current_chunk = overlap_chunk + [sentence]
                current_size = overlap_size + sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

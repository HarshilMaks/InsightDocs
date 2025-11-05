"""Document processing utilities."""
from typing import Dict, Any, List
import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles document parsing and transformation."""
    
    async def parse_document(self, file_path: str) -> Dict[str, Any]:
        """Parse a document and extract text content.
        
        Args:
            file_path: Path to the document
            
        Returns:
            Dictionary with parsed content and metadata
        """
        file_path_obj = Path(file_path)
        file_ext = file_path_obj.suffix.lower()
        
        # Simple text extraction (in production, use libraries like PyPDF2, python-docx, etc.)
        if file_ext == ".txt":
            return await self._parse_text_file(file_path)
        elif file_ext == ".pdf":
            return await self._parse_pdf_file(file_path)
        elif file_ext in [".doc", ".docx"]:
            return await self._parse_word_file(file_path)
        else:
            return {
                "text": "",
                "metadata": {"error": f"Unsupported file type: {file_ext}"}
            }
    
    async def _parse_text_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            return {
                "text": text,
                "metadata": {
                    "type": "text",
                    "char_count": len(text)
                }
            }
        except Exception as e:
            logger.error(f"Error parsing text file: {e}")
            return {"text": "", "metadata": {"error": str(e)}}
    
    async def _parse_pdf_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a PDF file."""
        # Placeholder - in production, use PyPDF2 or pdfplumber
        return {
            "text": "PDF content placeholder",
            "metadata": {"type": "pdf", "note": "PDF parsing not yet implemented"}
        }
    
    async def _parse_word_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a Word document."""
        # Placeholder - in production, use python-docx
        return {
            "text": "Word document content placeholder",
            "metadata": {"type": "docx", "note": "Word parsing not yet implemented"}
        }
    
    async def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[str]:
        """Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum size of each chunk
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        # Split by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > chunk_size and current_chunk:
                # Save current chunk
                chunks.append(' '.join(current_chunk))
                
                # Start new chunk with overlap
                overlap_text = ' '.join(current_chunk)
                if len(overlap_text) > overlap:
                    # Keep last part for overlap
                    current_chunk = [sentence]
                    current_size = sentence_size
                else:
                    current_chunk = [sentence]
                    current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

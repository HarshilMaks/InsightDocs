"""Enhanced PDF parser using PyMuPDF (fitz) for spatial text extraction."""
import logging
from typing import List, Dict, Any, Tuple, Optional
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFBlock:
    """Represents a text block with spatial positioning."""
    
    def __init__(
        self,
        text: str,
        page_number: int,
        bbox: Tuple[float, float, float, float],
        block_type: str = "text"
    ):
        self.text = text
        self.page_number = page_number
        self.bbox = bbox  # (x0, y0, x1, y1)
        self.block_type = block_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "page_number": self.page_number,
            "bbox": {
                "x1": self.bbox[0],
                "y1": self.bbox[1],
                "x2": self.bbox[2],
                "y2": self.bbox[3]
            },
            "type": self.block_type
        }


class EnhancedPDFParser:
    """Enhanced PDF parser with spatial text extraction using PyMuPDF."""
    
    def __init__(self):
        self.min_text_length = 10  # Minimum chars per block
    
    def parse_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Parse PDF and extract text with bounding boxes.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary with:
                - text: Full text content
                - blocks: List of PDFBlock objects with spatial data
                - metadata: Document metadata
        """
        try:
            doc = fitz.open(file_path)
            all_blocks: List[PDFBlock] = []
            full_text_parts: List[str] = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_blocks = self._extract_page_blocks(page, page_num + 1)
                all_blocks.extend(page_blocks)
                
                # Build full text (page separator)
                page_text = "\n".join(block.text for block in page_blocks)
                if page_text.strip():
                    full_text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
            
            full_text = "\n\n".join(full_text_parts)
            
            metadata = {
                "type": "pdf",
                "page_count": len(doc),
                "char_count": len(full_text),
                "block_count": len(all_blocks),
                "is_scanned": self._detect_scanned(doc),
                "has_spatial_data": True
            }
            
            doc.close()
            
            return {
                "text": full_text,
                "blocks": [block.to_dict() for block in all_blocks],
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error parsing PDF with PyMuPDF: {e}")
            return {
                "text": "",
                "blocks": [],
                "metadata": {"error": str(e)}
            }
    
    def _extract_page_blocks(self, page: fitz.Page, page_number: int) -> List[PDFBlock]:
        """
        Extract text blocks from a page with bounding boxes.
        
        Args:
            page: PyMuPDF Page object
            page_number: Page number (1-indexed)
            
        Returns:
            List of PDFBlock objects
        """
        blocks: List[PDFBlock] = []
        
        # Get page blocks (PyMuPDF returns blocks as tuples)
        page_dict = page.get_text("dict")
        
        for block in page_dict.get("blocks", []):
            # Type 0 = text block, Type 1 = image block
            if block.get("type") == 0:  # Text block
                block_text_parts = []
                bbox = block.get("bbox")  # (x0, y0, x1, y1)
                
                # Extract lines from the block
                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                    if line_text.strip():
                        block_text_parts.append(line_text.strip())
                
                block_text = " ".join(block_text_parts)
                
                # Only add non-empty blocks
                if block_text.strip() and len(block_text) >= self.min_text_length:
                    blocks.append(PDFBlock(
                        text=block_text,
                        page_number=page_number,
                        bbox=bbox,
                        block_type="text"
                    ))
        
        return blocks
    
    def _detect_scanned(self, doc: fitz.Document) -> bool:
        """
        Detect if PDF is scanned (image-based).
        
        Args:
            doc: PyMuPDF Document
            
        Returns:
            True if scanned, False otherwise
        """
        if len(doc) == 0:
            return False
        
        # Sample first 3 pages
        sample_pages = min(3, len(doc))
        total_text_len = 0
        total_images = 0
        
        for page_num in range(sample_pages):
            page = doc[page_num]
            text = page.get_text()
            total_text_len += len(text.strip())
            
            # Count images
            image_list = page.get_images()
            total_images += len(image_list)
        
        # If very little text but many images, likely scanned
        avg_text_per_page = total_text_len / sample_pages
        avg_images_per_page = total_images / sample_pages
        
        return avg_text_per_page < 100 and avg_images_per_page >= 1
    
    def chunk_blocks(
        self,
        blocks: List[Dict[str, Any]],
        chunk_size: int = 500,
        overlap: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Chunk text blocks while preserving spatial data.
        
        Args:
            blocks: List of block dictionaries
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks
            
        Returns:
            List of chunk dictionaries with bbox data
        """
        chunks: List[Dict[str, Any]] = []
        current_chunk_text = ""
        current_chunk_blocks: List[Dict[str, Any]] = []
        
        for block in blocks:
            block_text = block["text"]
            
            # If adding this block exceeds chunk_size, finalize current chunk
            if len(current_chunk_text) + len(block_text) > chunk_size and current_chunk_blocks:
                # Create chunk with first block's bbox (approximation)
                first_block = current_chunk_blocks[0]
                chunks.append({
                    "text": current_chunk_text.strip(),
                    "page_number": first_block["page_number"],
                    "bbox": first_block["bbox"]
                })
                
                # Start new chunk with overlap (last N chars)
                overlap_text = current_chunk_text[-overlap:] if len(current_chunk_text) > overlap else ""
                current_chunk_text = overlap_text + " " + block_text
                current_chunk_blocks = [block]
            else:
                current_chunk_text += " " + block_text
                current_chunk_blocks.append(block)
        
        # Add final chunk
        if current_chunk_blocks:
            first_block = current_chunk_blocks[0]
            chunks.append({
                "text": current_chunk_text.strip(),
                "page_number": first_block["page_number"],
                "bbox": first_block["bbox"]
            })
        
        return chunks

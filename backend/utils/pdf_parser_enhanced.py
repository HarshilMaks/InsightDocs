"""Enhanced PDF parser using PyMuPDF (fitz) for spatial text extraction."""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False
    logger.warning("PyMuPDF (fitz) not available. PDF spatial extraction will be disabled.")



class PDFBlock:
    """Represents a text block with spatial positioning."""
    
    def __init__(
        self,
        text: str,
        page_number: int,
        bbox: Tuple[float, float, float, float],
        block_type: str = "text",
        avg_font_size: Optional[float] = None,
    ):
        self.text = text
        self.page_number = page_number
        self.bbox = bbox  # (x0, y0, x1, y1)
        self.block_type = block_type
        self.avg_font_size = avg_font_size
    
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
            "type": self.block_type,
            "avg_font_size": self.avg_font_size,
        }


class EnhancedPDFParser:
    """Enhanced PDF parser with spatial text extraction using PyMuPDF."""
    
    def __init__(self):
        if not FITZ_AVAILABLE:
            logger.warning("EnhancedPDFParser initialized without PyMuPDF support")
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
        if not FITZ_AVAILABLE:
            raise RuntimeError("PyMuPDF (fitz) is not installed. Cannot parse PDF with spatial extraction.")
        
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
                span_sizes: List[float] = []
                
                # Extract lines from the block
                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                        size = span.get("size")
                        if size:
                            span_sizes.append(float(size))
                    if line_text.strip():
                        block_text_parts.append(line_text.strip())
                
                block_text = " ".join(block_text_parts)
                avg_font_size = sum(span_sizes) / len(span_sizes) if span_sizes else None
                
                # Only add non-empty blocks
                if block_text.strip() and len(block_text) >= self.min_text_length:
                    blocks.append(PDFBlock(
                        text=block_text,
                        page_number=page_number,
                        bbox=bbox,
                        block_type="text",
                        avg_font_size=avg_font_size,
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
    
    # Heading candidates must be shorter than this (headings are short by
    # nature; long lines at a larger font size are more likely a pull-quote
    # or emphasized paragraph than a section title).
    _MAX_HEADING_LENGTH = 120
    # A block's average font size must exceed the page's median body-text
    # size by at least this ratio to be treated as a heading.
    _HEADING_FONT_RATIO = 1.15

    def _is_table_bbox_match(
        self,
        block_bbox: Dict[str, float],
        page_number: int,
        tables: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Return the table dict a block overlaps with, if any.

        A block is considered part of a table when its bbox center falls
        inside a table's bbox on the same page. This lets chunk_blocks()
        exclude prose blocks that pdfplumber already captured as table
        cells, so a table is never duplicated as both atomic table text
        and fragmented prose chunks.
        """
        block_cx = (block_bbox["x1"] + block_bbox["x2"]) / 2
        block_cy = (block_bbox["y1"] + block_bbox["y2"]) / 2
        for table in tables:
            if table.get("page_number") != page_number:
                continue
            tbbox = table.get("bbox") or {}
            if not tbbox:
                continue
            if tbbox["x1"] <= block_cx <= tbbox["x2"] and tbbox["y1"] <= block_cy <= tbbox["y2"]:
                return table
        return None

    def _detect_section_headings(self, blocks: List[Dict[str, Any]]) -> Dict[int, str]:
        """Identify which block indices are section headings.

        Uses a simple, document-relative heuristic: a block is a heading
        candidate if it is short and its average font size is noticeably
        larger than the median font size of body-text blocks in the
        document. This avoids hardcoding an absolute font size, since that
        varies a lot between documents.

        Returns a mapping of block index -> heading text.
        """
        font_sizes = [
            b["avg_font_size"]
            for b in blocks
            if b.get("avg_font_size") and len(b.get("text", "")) > self._MAX_HEADING_LENGTH
        ]
        if not font_sizes:
            # No reliable body-text baseline (e.g. OCR text with no font
            # metadata) — heading detection is skipped, not guessed.
            return {}

        sorted_sizes = sorted(font_sizes)
        median_body_size = sorted_sizes[len(sorted_sizes) // 2]
        if median_body_size <= 0:
            return {}

        headings: Dict[int, str] = {}
        for idx, block in enumerate(blocks):
            text = block.get("text", "").strip()
            size = block.get("avg_font_size")
            if not text or not size or len(text) > self._MAX_HEADING_LENGTH:
                continue
            if size >= median_body_size * self._HEADING_FONT_RATIO:
                headings[idx] = text
        return headings

    def chunk_blocks(
        self,
        blocks: List[Dict[str, Any]],
        chunk_size: int = 500,
        overlap: int = 100,
        tables: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Chunk text blocks while preserving spatial data, document structure,
        and table atomicity.

        Behavior:
        - Blocks that fall inside a detected table's bounding box are
          excluded from prose chunking; the table is instead emitted once,
          in page order, as a single atomic chunk (never split), using its
          markdown representation.
        - Section headings (detected via a font-size heuristic) start a new
          "section". Every chunk records the section_title of the heading
          that precedes it, so retrieval can surface which section an
          answer came from.
        - Each section's child chunks are linked to one synthetic parent
          chunk per section via parent_chunk_index, so retrieval can hydrate
          a wider context window around a precisely-matched child chunk.

        Args:
            blocks: List of block dictionaries (as produced by
                EnhancedPDFParser._extract_page_blocks / .to_dict())
            chunk_size: Target chunk size in characters for prose chunks
            overlap: Overlap between prose chunks
            tables: Optional list of table dicts (as produced by
                TableExtractor), used to keep tables atomic and to exclude
                their text from prose chunking

        Returns:
            List of chunk dictionaries, each with: text, page_number, bbox,
            chunk_type ("text" | "table"), section_title, and
            parent_chunk_index (index into the same list identifying this
            chunk's parent section chunk; a parent's own parent_chunk_index
            is None).
        """
        tables = tables or []
        headings = self._detect_section_headings(blocks)

        # Filter out any block that overlaps a table region so table text
        # is never duplicated as fragmented prose.
        filtered_blocks: List[Dict[str, Any]] = []
        for block in blocks:
            bbox = block.get("bbox") or {}
            if bbox and self._is_table_bbox_match(bbox, block.get("page_number"), tables):
                continue
            filtered_blocks.append(block)

        chunks: List[Dict[str, Any]] = []
        current_section_title: Optional[str] = None
        current_chunk_text = ""
        current_chunk_blocks: List[Dict[str, Any]] = []
        # Maps section_title -> index of that section's parent chunk in `chunks`
        section_parent_index: Dict[Optional[str], int] = {}

        def _ensure_parent_for_section(section_title: Optional[str], first_block: Dict[str, Any]) -> int:
            """Create (once) a parent chunk representing this section and
            return its index. The parent's text accumulates the full
            section so the LLM can be given wider context than a single
            child chunk when needed."""
            if section_title in section_parent_index:
                return section_parent_index[section_title]
            parent_chunk = {
                "text": "",
                "page_number": first_block["page_number"],
                "bbox": first_block["bbox"],
                "chunk_type": "text",
                "section_title": section_title,
                "parent_chunk_index": None,
                "is_parent": True,
            }
            chunks.append(parent_chunk)
            section_parent_index[section_title] = len(chunks) - 1
            return len(chunks) - 1

        def _union_chunk_bbox(chunk_blocks: List[Dict[str, Any]]) -> Optional[Dict[str, float]]:
            """Return one visible same-page rectangle covering every child block."""
            bboxes = [block.get("bbox") or {} for block in chunk_blocks]
            valid = [
                bbox for bbox in bboxes
                if all(key in bbox for key in ("x1", "y1", "x2", "y2"))
            ]
            if not valid:
                return None
            return {
                "x1": min(float(bbox["x1"]) for bbox in valid),
                "y1": min(float(bbox["y1"]) for bbox in valid),
                "x2": max(float(bbox["x2"]) for bbox in valid),
                "y2": max(float(bbox["y2"]) for bbox in valid),
            }

        def _finalize_prose_chunk():
            nonlocal current_chunk_text, current_chunk_blocks
            if not current_chunk_blocks:
                return
            first_block = current_chunk_blocks[0]
            parent_idx = _ensure_parent_for_section(current_section_title, first_block)
            chunks.append({
                "text": current_chunk_text.strip(),
                "page_number": first_block["page_number"],
                "bbox": _union_chunk_bbox(current_chunk_blocks),
                "chunk_type": "text",
                "section_title": current_section_title,
                "parent_chunk_index": parent_idx,
            })
            chunks[parent_idx]["text"] = (
                chunks[parent_idx]["text"] + " " + current_chunk_text.strip()
            ).strip()
            current_chunk_text = ""
            current_chunk_blocks = []

        for idx, block in enumerate(blocks):
            bbox = block.get("bbox") or {}
            matched_table = (
                self._is_table_bbox_match(bbox, block.get("page_number"), tables) if bbox else None
            )
            if matched_table is not None:
                # Table regions are handled separately below via the
                # dedicated table-emission pass, so we don't process the
                # underlying prose block here at all (it was already
                # excluded from filtered_blocks).
                continue

            if current_chunk_blocks and block.get("page_number") != current_chunk_blocks[0].get("page_number"):
                # A single bbox cannot truthfully describe content across two
                # pages. Finish the current page before starting the next.
                _finalize_prose_chunk()

            if idx in headings:
                # A new heading finalizes the current prose chunk and
                # starts a new section.
                _finalize_prose_chunk()
                current_section_title = headings[idx]
                continue

            block_text = block.get("text", "")
            if not block_text:
                continue

            if len(current_chunk_text) + len(block_text) > chunk_size and current_chunk_blocks:
                _finalize_prose_chunk()
                overlap_text = current_chunk_text[-overlap:] if len(current_chunk_text) > overlap else ""
                current_chunk_text = (overlap_text + " " + block_text).strip()
                current_chunk_blocks = [block]
            else:
                current_chunk_text = (current_chunk_text + " " + block_text).strip()
                current_chunk_blocks.append(block)

        _finalize_prose_chunk()

        # Emit each table as a single atomic chunk, in page order, using
        # its markdown representation so the table structure is preserved
        # for the LLM rather than flattened into unstructured text.
        table_chunks = []
        for table in sorted(tables, key=lambda t: (t.get("page_number", 0), t.get("table_index", 0))):
            table_bbox = table.get("bbox") or {}
            table_chunks.append({
                "text": table.get("markdown", ""),
                "page_number": table.get("page_number"),
                "bbox": table_bbox,
                "chunk_type": "table",
                "section_title": current_section_title,
                "parent_chunk_index": None,
            })

        all_chunks = chunks + table_chunks

        # Parent chunks with no child content (e.g. a heading immediately
        # followed by another heading) contribute nothing useful; drop them
        # but keep their children's parent_chunk_index valid by leaving
        # indices as-is only when the parent had text. Empty parents are
        # rare and harmless to keep as a zero-length record, so we simply
        # strip fully empty ones here without renumbering, since no other
        # chunk points at an empty parent that never received text.
        return [c for c in all_chunks if c.get("text", "").strip() or c.get("chunk_type") == "table"]

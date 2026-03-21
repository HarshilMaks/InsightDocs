"""Enhanced table extraction using pdfplumber."""
import logging
from typing import List, Dict, Any, Optional
import pdfplumber

logger = logging.getLogger(__name__)


class TableExtractor:
    """Extract tables from PDF documents using pdfplumber."""
    
    def __init__(self):
        self.table_settings = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "edge_min_length": 3,
            "min_words_vertical": 3,
            "min_words_horizontal": 1,
        }
    
    def extract_tables_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract all tables from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of table dictionaries with metadata
        """
        tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = self._extract_tables_from_page(page, page_num)
                    tables.extend(page_tables)
            
            logger.info(f"Extracted {len(tables)} tables from {pdf_path}")
            return tables
            
        except Exception as e:
            logger.error(f"Error extracting tables from PDF: {e}")
            return []
    
    def _extract_tables_from_page(self, page: pdfplumber.page.Page, page_num: int) -> List[Dict[str, Any]]:
        """Extract tables from a single page."""
        page_tables = []
        
        try:
            # Find tables using pdfplumber's table detection
            tables = page.find_tables(table_settings=self.table_settings)
            
            for table_idx, table in enumerate(tables):
                # Extract table data
                table_data = table.extract()
                
                if not table_data or len(table_data) < 2:
                    continue  # Skip empty or single-row tables
                
                # Get table bounding box
                bbox = table.bbox  # (x0, y0, x1, y1)
                
                # Format table as structured data
                headers = table_data[0] if table_data else []
                rows = table_data[1:] if len(table_data) > 1 else []
                
                # Convert to markdown for text representation
                markdown = self._table_to_markdown(headers, rows)
                
                page_tables.append({
                    "page_number": page_num,
                    "table_index": table_idx,
                    "bbox": {
                        "x1": bbox[0],
                        "y1": bbox[1],
                        "x2": bbox[2],
                        "y2": bbox[3]
                    },
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows),
                    "col_count": len(headers),
                    "markdown": markdown,
                    "type": "table"
                })
            
        except Exception as e:
            logger.error(f"Error extracting tables from page {page_num}: {e}")
        
        return page_tables
    
    @staticmethod
    def _table_to_markdown(headers: List[str], rows: List[List[str]]) -> str:
        """Convert table to markdown format."""
        if not headers:
            return ""
        
        # Create header row
        header_row = "| " + " | ".join(str(h or "") for h in headers) + " |"
        separator = "| " + " | ".join("---" for _ in headers) + " |"
        
        # Create data rows
        data_rows = []
        for row in rows:
            # Pad row if needed
            padded_row = row + [""] * (len(headers) - len(row))
            row_str = "| " + " | ".join(str(cell or "") for cell in padded_row[:len(headers)]) + " |"
            data_rows.append(row_str)
        
        # Combine all parts
        markdown_lines = [header_row, separator] + data_rows
        return "\n".join(markdown_lines)
    
    def extract_text_and_tables(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract both text and tables from PDF, preserving layout.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with text, tables, and combined content
        """
        all_text_blocks = []
        all_tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract tables
                    page_tables = self._extract_tables_from_page(page, page_num)
                    all_tables.extend(page_tables)
                    
                    # Extract text (excluding table regions)
                    # Get table bounding boxes
                    table_bboxes = [t.bbox for t in page.find_tables(table_settings=self.table_settings)]
                    
                    # Get text outside tables
                    if table_bboxes:
                        # Filter out text that falls within table regions
                        words = page.extract_words()
                        non_table_words = [
                            w for w in words
                            if not any(self._is_word_in_bbox(w, bbox) for bbox in table_bboxes)
                        ]
                        text = " ".join(w["text"] for w in non_table_words)
                    else:
                        text = page.extract_text()
                    
                    if text and text.strip():
                        all_text_blocks.append({
                            "page_number": page_num,
                            "text": text.strip(),
                            "type": "text"
                        })
            
            # Combine text and tables in page order
            combined_content = self._combine_text_and_tables(all_text_blocks, all_tables)
            
            return {
                "text_blocks": all_text_blocks,
                "tables": all_tables,
                "combined_text": combined_content,
                "metadata": {
                    "text_block_count": len(all_text_blocks),
                    "table_count": len(all_tables)
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting text and tables: {e}")
            return {
                "text_blocks": [],
                "tables": [],
                "combined_text": "",
                "metadata": {"error": str(e)}
            }
    
    @staticmethod
    def _is_word_in_bbox(word: dict, bbox: tuple) -> bool:
        """Check if a word falls within a bounding box."""
        wx0, wy0, wx1, wy1 = word["x0"], word["top"], word["x1"], word["bottom"]
        bx0, by0, bx1, by1 = bbox
        
        # Check if word center is inside bbox
        word_center_x = (wx0 + wx1) / 2
        word_center_y = (wy0 + wy1) / 2
        
        return bx0 <= word_center_x <= bx1 and by0 <= word_center_y <= by1
    
    @staticmethod
    def _combine_text_and_tables(text_blocks: List[Dict], tables: List[Dict]) -> str:
        """Combine text blocks and tables in reading order."""
        # Merge and sort by page number
        all_content = text_blocks + tables
        all_content.sort(key=lambda x: x["page_number"])
        
        combined = []
        current_page = None
        
        for item in all_content:
            # Add page separator
            if item["page_number"] != current_page:
                current_page = item["page_number"]
                combined.append(f"\n--- Page {current_page} ---\n")
            
            # Add content
            if item["type"] == "text":
                combined.append(item["text"])
            elif item["type"] == "table":
                combined.append(f"\n[Table {item['table_index'] + 1}]\n{item['markdown']}\n")
        
        return "\n\n".join(combined)


# Singleton instance
_extractor = TableExtractor()

def extract_tables(pdf_path: str) -> List[Dict[str, Any]]:
    """Extract tables from PDF."""
    return _extractor.extract_tables_from_pdf(pdf_path)

def extract_text_and_tables(pdf_path: str) -> Dict[str, Any]:
    """Extract both text and tables from PDF."""
    return _extractor.extract_text_and_tables(pdf_path)

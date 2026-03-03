"""
OCR Processing Module for InsightDocs

Handles detection and extraction of text from scanned PDFs and images
using Tesseract OCR.
"""

import logging
from typing import Optional, Tuple
from pathlib import Path
import io

try:
    import pytesseract
    from pytesseract import Output
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    logging.warning("pytesseract not available. OCR features will be disabled.")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("Pillow not available. Image processing will be disabled.")

try:
    import fitz  # PyMuPDF for PDF processing
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False
    logging.warning("PyMuPDF not available. PDF scanning will be limited.")

logger = logging.getLogger(__name__)


class OcrProcessor:
    """
    OCR processor for extracting text from scanned PDFs and images.
    """

    # OCR confidence threshold (0-100). Below this, text is considered scanned.
    SCANNED_THRESHOLD = 0.3  # 30% of text detected = likely scanned
    
    # Confidence score threshold for individual OCR results
    CONFIDENCE_THRESHOLD = 0.5  # 50% confidence minimum

    @staticmethod
    def is_pytesseract_available() -> bool:
        """Check if Tesseract OCR is available."""
        if not PYTESSERACT_AVAILABLE:
            return False
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception as e:
            logger.warning(f"Tesseract not available: {e}")
            return False

    @staticmethod
    def detect_scanned_pdf(pdf_path: str) -> Tuple[bool, float]:
        """
        Detect if a PDF is scanned (image-based) or text-based.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (is_scanned, confidence_score)
            - is_scanned: True if PDF appears to be scanned
            - confidence_score: 0-1, how confident the detection is
        """
        if not FITZ_AVAILABLE:
            logger.warning("PyMuPDF not available. Cannot detect scanned PDFs.")
            return False, 0.0

        try:
            doc = fitz.open(pdf_path)
            
            # Sample first 3 pages (or fewer if PDF is shorter)
            pages_to_check = min(3, doc.page_count)
            text_block_count = 0
            total_area = 0
            
            for page_num in range(pages_to_check):
                page = doc[page_num]
                
                # Get all text blocks
                blocks = page.get_text("blocks")
                text_block_count += len(blocks)
                
                # Get page area
                rect = page.rect
                total_area += rect.get_area()
            
            doc.close()
            
            # If few text blocks relative to area, likely scanned
            avg_blocks_per_page = text_block_count / pages_to_check
            avg_area_per_page = total_area / pages_to_check
            
            # Heuristic: scanned PDFs have < 5 text blocks per page on average
            text_density = avg_blocks_per_page / (avg_area_per_page / 1000000) if avg_area_per_page > 0 else 0
            
            # More aggressive: if less than 3 text blocks per page, likely scanned
            is_scanned = avg_blocks_per_page < 3
            confidence = min(1.0, abs(3 - avg_blocks_per_page) / 3)  # Normalize confidence
            
            logger.info(f"PDF scan detection: is_scanned={is_scanned}, confidence={confidence:.2f}, blocks={avg_blocks_per_page}")
            return is_scanned, confidence
            
        except Exception as e:
            logger.error(f"Error detecting scanned PDF: {e}")
            return False, 0.0

    @staticmethod
    def extract_text_from_image(image_path: str) -> Tuple[str, float]:
        """
        Extract text from an image using Tesseract OCR.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple of (extracted_text, confidence_score)
            - extracted_text: OCR'd text
            - confidence_score: 0-1, average confidence of extraction
        """
        if not PYTESSERACT_AVAILABLE:
            logger.error("Tesseract not available for OCR")
            return "", 0.0

        if not PIL_AVAILABLE:
            logger.error("Pillow not available for image processing")
            return "", 0.0

        try:
            image = Image.open(image_path)
            
            # Get detailed OCR results with confidence
            ocr_data = pytesseract.image_to_data(image, output_type=Output.DICT)
            
            text_parts = []
            confidences = []
            
            for i, text in enumerate(ocr_data['text']):
                if text.strip():  # Skip empty text
                    text_parts.append(text)
                    conf = int(ocr_data['conf'][i])
                    if conf >= 0:  # Confidence -1 means no text detected
                        confidences.append(conf / 100.0)
            
            extracted_text = ' '.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            logger.info(f"OCR extraction: {len(extracted_text)} chars, confidence={avg_confidence:.2f}")
            return extracted_text, avg_confidence
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return "", 0.0

    @staticmethod
    def process_scanned_pdf(pdf_path: str) -> Tuple[str, float]:
        """
        Process a scanned PDF by converting pages to images and running OCR.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (extracted_text, avg_confidence)
            - extracted_text: All OCR'd text from PDF
            - avg_confidence: Average confidence score
        """
        if not FITZ_AVAILABLE:
            logger.error("PyMuPDF required for PDF OCR processing")
            return "", 0.0

        if not PYTESSERACT_AVAILABLE:
            logger.error("Tesseract required for OCR")
            return "", 0.0

        try:
            doc = fitz.open(pdf_path)
            all_text = []
            all_confidences = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Render page as image (300 DPI for better OCR)
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                
                # Convert to PIL Image
                image_data = pix.tobytes("ppm")
                image = Image.open(io.BytesIO(image_data))
                
                # Run OCR on page image
                text, confidence = OcrProcessor.extract_text_from_image_object(image)
                
                if text:
                    all_text.append(text)
                    all_confidences.append(confidence)
            
            doc.close()
            
            final_text = '\n'.join(all_text)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            
            logger.info(f"PDF OCR complete: {len(final_text)} chars, pages={len(all_text)}, avg_conf={avg_confidence:.2f}")
            return final_text, avg_confidence
            
        except Exception as e:
            logger.error(f"Error processing scanned PDF: {e}")
            return "", 0.0

    @staticmethod
    def extract_text_from_image_object(image: 'Image.Image') -> Tuple[str, float]:
        """
        Extract text from a PIL Image object using Tesseract OCR.
        
        Args:
            image: PIL Image object
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        if not PYTESSERACT_AVAILABLE:
            return "", 0.0

        try:
            ocr_data = pytesseract.image_to_data(image, output_type=Output.DICT)
            
            text_parts = []
            confidences = []
            
            for i, text in enumerate(ocr_data['text']):
                if text.strip():
                    text_parts.append(text)
                    conf = int(ocr_data['conf'][i])
                    if conf >= 0:
                        confidences.append(conf / 100.0)
            
            extracted_text = ' '.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return extracted_text, avg_confidence
            
        except Exception as e:
            logger.error(f"Error in OCR: {e}")
            return "", 0.0
